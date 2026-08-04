# Unavailable dynamics and safety evidence

The imported asset exposes the nine revolute joint prims and the three active Delta inputs, but this run is a reference-state/kinematic playback. The importer reported that no mass was specified for `body`, and the run did not establish a complete closed-chain articulation dynamics model.

Contact query was not implemented in this playback harness and the clearance gate was not executed. These are recorded as missing evidence, not as zero contact or positive clearance.
