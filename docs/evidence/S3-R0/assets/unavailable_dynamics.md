# Unavailable dynamics and safety evidence

The imported asset exposes the nine revolute joint prims and the three active Delta inputs, but this run is a reference-state/kinematic playback. The importer reported that no mass was specified for `body`, and the run did not establish a complete closed-chain articulation dynamics model.

The playback harness now runs a PhysX scene-query overlap probe. It reports no non-scene hits and no hits in the 0.010 m expanded obstacle boxes. This is a conservative clearance lower-bound probe, not an exact closest-distance computation; the exact minimum distance and S2 delta remain unavailable.
