from __future__ import annotations

import argparse
import sys
import time

import rospy
from sensor_msgs.msg import PointCloud2
from sensor_msgs import point_cloud2
from std_msgs.msg import Header

from generate_s2_r2_crossarm_map import build_points


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", required=True, choices=("smoke_free", "loose", "nominal", "narrow"))
    parser.add_argument("--topic", default="/global_map")
    args = parser.parse_args(rospy.myargv()[1:])
    rospy.init_node("s2_r2_crossarm_map_publisher", anonymous=True)
    publisher = rospy.Publisher(args.topic, PointCloud2, queue_size=1, latch=True)
    points = build_points(args.variant)
    rate = rospy.Rate(5)
    while not rospy.is_shutdown():
        header = Header(stamp=rospy.Time.now(), frame_id="world")
        publisher.publish(point_cloud2.create_cloud_xyz32(header, points))
        rate.sleep()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
