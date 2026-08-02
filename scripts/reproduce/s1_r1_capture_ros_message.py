#!/usr/bin/env python3
"""Capture the first nonempty AM-Planner trajectory message on both topics."""
import argparse
import json
import math
import os
import sys
import threading
import time

import rospy
import roslib.message


def convert(value, stats):
    if hasattr(value, "__slots__"):
        return {slot: convert(getattr(value, slot), stats) for slot in value.__slots__}
    if isinstance(value, (list, tuple)):
        return [convert(item, stats) for item in value]
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        stats["numeric_fields"] += 1
        number = float(value)
        if math.isnan(number):
            stats["nan_count"] += 1
            return "NaN"
        elif math.isinf(number):
            stats["inf_count"] += 1
            return "Infinity" if number > 0 else "-Infinity"
        else:
            stats["finite_numeric_fields"] += 1
            if number != 0.0: stats["nonzero_numeric_fields"] += 1
            if number > 0.0: stats["positive_numeric_fields"] += 1
        return value
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--timeout-s", type=float, required=True)
    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    rospy.init_node("s1_r1_trajectory_capture", anonymous=True, disable_signals=True)
    received, locks = {}, {"/trajectory": threading.Lock(), "/trajectory_arm": threading.Lock()}

    def callback(topic):
        def record(message):
            with locks[topic]:
                if topic in received:
                    return
                stats = {"numeric_fields": 0, "finite_numeric_fields": 0, "nan_count": 0,
                         "inf_count": 0, "nonzero_numeric_fields": 0, "positive_numeric_fields": 0}
                payload = convert(message, stats)
                received[topic] = {"topic": topic, "message_type": message._type,
                                   "received_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                   "field_count": len(message.__slots__), "statistics": stats,
                                   "message": payload}
        return record

    subscribers = []
    for topic in locks:
        _, _, topic_types = rospy.get_master().getTopicTypes()
        discovered = dict(topic_types).get(topic)
        if discovered:
            message_class = roslib.message.get_message_class(discovered)
            if message_class:
                subscribers.append(rospy.Subscriber(topic, message_class, callback(topic), queue_size=1))
    deadline = time.monotonic() + args.timeout_s
    while time.monotonic() < deadline and len(received) < 2 and not rospy.is_shutdown():
        for topic in locks:
            if topic in received or any(sub.resolved_name == topic for sub in subscribers):
                continue
            _, _, topic_types = rospy.get_master().getTopicTypes()
            discovered = dict(topic_types).get(topic)
            message_class = roslib.message.get_message_class(discovered) if discovered else None
            if message_class:
                subscribers.append(rospy.Subscriber(topic, message_class, callback(topic), queue_size=1))
        time.sleep(0.2)
    for topic, entry in received.items():
        filename = "trajectory.json" if topic == "/trajectory" else "trajectory_arm.json"
        with open(os.path.join(args.output_dir, filename), "w", encoding="utf-8") as handle:
            json.dump(entry, handle, ensure_ascii=False, indent=2, allow_nan=False)
    summary = {"received_topics": sorted(received), "expected_topics": sorted(locks),
               "timeout_s": args.timeout_s, "success": len(received) == 2}
    summary.update({topic: value["statistics"] for topic, value in received.items()})
    with open(os.path.join(args.output_dir, "numeric_validation.json"), "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    return 0 if summary["success"] else 2


if __name__ == "__main__":
    sys.exit(main())
