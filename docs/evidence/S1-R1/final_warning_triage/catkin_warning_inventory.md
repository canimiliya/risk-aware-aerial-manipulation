# Catkin warning inventory

- Raw log: `docs/evidence/S1-R1/r7r3_r1_integration/build_attempt_02.log`
- Warning-bearing packages: **8**
- Policy: raw warning text is preserved; this inventory does not filter warnings.

| Package | Warning count | Stages | Source category |
|---|---:|---|---|
| `octomap_server` | 10 | cmake | ROS/CMake |
| `map_pcl` | 4 | cmake | 官方第三方源码/编译器提示; ROS/CMake |
| `so3_control` | 2 | cmake | ROS/CMake |
| `so3_quadrotor_simulator` | 2 | cmake | ROS/CMake |
| `traj_server` | 7 | cmake, make | 官方第三方源码/编译器提示; 轨迹相关; 未使用变量/依赖 |
| `jps3d` | 14 | cmake, make | 官方第三方源码/编译器提示; ROS/CMake |
| `traj_opt` | 11 | cmake, make | ROS/CMake; 官方第三方源码/编译器提示; 未使用变量/依赖 |
| `plan_manage` | 2 | cmake, make | ROS/CMake; 官方第三方源码/编译器提示 |

## Warning summaries

### `octomap_server`

- Files: `/home/amplanner/am-planner-r7r3-r1-ws/logs/octomap_server/build.cmake.001.log`
- Classification: ROS/CMake
- Deduplicated raw warning lines:
  - `CMake Warning at /home/amplanner/am-planner-r7r3-r1-ws/src/src/plan/uitls/octomap_server/CMakeLists.txt:73 (add_library):`
  - `CMake Warning at /home/amplanner/am-planner-r7r3-r1-ws/src/src/plan/uitls/octomap_server/CMakeLists.txt:66 (add_executable):`
  - `CMake Warning at /home/amplanner/am-planner-r7r3-r1-ws/src/src/plan/uitls/octomap_server/CMakeLists.txt:60 (add_executable):`
  - `CMake Warning at /home/amplanner/am-planner-r7r3-r1-ws/src/src/plan/uitls/octomap_server/CMakeLists.txt:57 (add_executable):`
  - `CMake Warning at /home/amplanner/am-planner-r7r3-r1-ws/src/src/plan/uitls/octomap_server/CMakeLists.txt:54 (add_executable):`
  - `CMake Warning at /home/amplanner/am-planner-r7r3-r1-ws/src/src/plan/uitls/octomap_server/CMakeLists.txt:76 (add_library):`
  - `CMake Warning at /home/amplanner/am-planner-r7r3-r1-ws/src/src/plan/uitls/octomap_server/CMakeLists.txt:45 (add_library):`
  - `CMake Warning at /home/amplanner/am-planner-r7r3-r1-ws/src/src/plan/uitls/octomap_server/CMakeLists.txt:69 (add_executable):`
  - `CMake Warning at /home/amplanner/am-planner-r7r3-r1-ws/src/src/plan/uitls/octomap_server/CMakeLists.txt:63 (add_executable):`
  - `CMake Warning at /home/amplanner/am-planner-r7r3-r1-ws/src/src/plan/uitls/octomap_server/CMakeLists.txt:49 (add_library):`

### `map_pcl`

- Files: `/home/amplanner/am-planner-r7r3-r1-ws/logs/map_pcl/build.cmake.001.log`
- Classification: 官方第三方源码/编译器提示, ROS/CMake
- Deduplicated raw warning lines:
  - `** WARNING ** io features related to pcap will be disabled`
  - `** WARNING ** io features related to png will be disabled`
  - `** WARNING ** io features related to libusb-1.0 will be disabled`
  - `CMake Warning at /home/amplanner/am-planner-r7r3-r1-ws/src/src/utils/map_pcl/CMakeLists.txt:24 (add_executable):`

### `so3_control`

- Files: `/home/amplanner/am-planner-r7r3-r1-ws/logs/so3_control/build.cmake.001.log`
- Classification: ROS/CMake
- Deduplicated raw warning lines:
  - `CMake Warning at /home/amplanner/am-planner-r7r3-r1-ws/src/src/uam_sim/so3_control/CMakeLists.txt:38 (add_executable):`
  - `CMake Warning at /home/amplanner/am-planner-r7r3-r1-ws/src/src/uam_sim/so3_control/CMakeLists.txt:31 (add_library):`

### `so3_quadrotor_simulator`

- Files: `/home/amplanner/am-planner-r7r3-r1-ws/logs/so3_quadrotor_simulator/build.cmake.001.log`
- Classification: ROS/CMake
- Deduplicated raw warning lines:
  - `CMake Warning at /opt/ros/noetic/share/catkin/cmake/catkin_package.cmake:166 (message):`

### `traj_server`

- Files: `/home/amplanner/am-planner-r7r3-r1-ws/logs/traj_server/build.cmake.001.log`, `/home/amplanner/am-planner-r7r3-r1-ws/logs/traj_server/build.make.000.log`
- Classification: 官方第三方源码/编译器提示, 轨迹相关, 未使用变量/依赖
- Deduplicated raw warning lines:
  - `** WARNING ** io features related to pcap will be disabled`
  - `** WARNING ** io features related to png will be disabled`
  - `** WARNING ** io features related to libusb-1.0 will be disabled`
  - `/home/amplanner/am-planner-r7r3-r1-ws/src/src/utils/traj_server/src/traj_server.cpp:447:22: warning: comparison between ‘enum TrajectoryServer::ArmState’ and ‘enum TrajectoryServer::ServerState’ [-Wenum-compare]`
  - `/home/amplanner/am-planner-r7r3-r1-ws/src/src/utils/traj_server/src/traj_server.cpp:476:11: warning: unused variable ‘cur_poly_num’ [-Wunused-variable]`
  - `/home/amplanner/am-planner-r7r3-r1-ws/src/src/utils/traj_server/src/traj_server.cpp:581:11: warning: unused variable ‘cur_poly_num’ [-Wunused-variable]`
  - `/home/amplanner/am-planner-r7r3-r1-ws/src/src/utils/traj_server/src/traj_server.cpp:808:29: warning: comparison of integer expressions of different signedness: ‘int’ and ‘const _num_segment_type’ {aka ‘const unsigned int’} [-Wsign-compare]`

### `jps3d`

- Files: `/home/amplanner/am-planner-r7r3-r1-ws/logs/jps3d/build.cmake.000.log`, `/home/amplanner/am-planner-r7r3-r1-ws/logs/jps3d/build.make.000.log`
- Classification: 官方第三方源码/编译器提示, ROS/CMake
- Deduplicated raw warning lines:
  - `** WARNING ** io features related to pcap will be disabled`
  - `** WARNING ** io features related to png will be disabled`
  - `** WARNING ** io features related to libusb-1.0 will be disabled`
  - `CMake Warning at /home/amplanner/am-planner-r7r3-r1-ws/src/src/plan/jps3d/CMakeLists.txt:40 (add_library):`
  - `/home/amplanner/am-planner-r7r3-r1-ws/src/src/plan/jps3d/src/jps_planner.cpp:140:21: warning: comparison of integer expressions of different signedness: ‘int’ and ‘std::vector<Eigen::Matrix<double, 2, 1>, Eigen::aligned_allocator<Eigen::Matrix<double, 2, 1> > >::size_type’ {aka ‘long unsigned int’} [-Wsign-compare]`
  - `/home/amplanner/am-planner-r7r3-r1-ws/src/src/plan/jps3d/src/jps_planner.cpp:201:21: warning: comparison of integer expressions of different signedness: ‘int’ and ‘std::vector<Eigen::Matrix<double, 2, 1>, Eigen::aligned_allocator<Eigen::Matrix<double, 2, 1> > >::size_type’ {aka ‘long unsigned int’} [-Wsign-compare]`
  - `/home/amplanner/am-planner-r7r3-r1-ws/src/src/plan/jps3d/src/jps_planner.cpp:217:21: warning: comparison of integer expressions of different signedness: ‘int’ and ‘std::vector<Eigen::Matrix<double, 2, 1>, Eigen::aligned_allocator<Eigen::Matrix<double, 2, 1> > >::size_type’ {aka ‘long unsigned int’} [-Wsign-compare]`
  - `/home/amplanner/am-planner-r7r3-r1-ws/src/src/plan/jps3d/src/jps_planner.cpp:254:21: warning: comparison of integer expressions of different signedness: ‘int’ and ‘std::vector<Eigen::Matrix<double, 2, 1>, Eigen::aligned_allocator<Eigen::Matrix<double, 2, 1> > >::size_type’ {aka ‘long unsigned int’} [-Wsign-compare]`
  - `/home/amplanner/am-planner-r7r3-r1-ws/src/src/plan/jps3d/src/jps_planner.cpp:288:21: warning: comparison of integer expressions of different signedness: ‘int’ and ‘std::vector<Eigen::Matrix<double, 2, 1>, Eigen::aligned_allocator<Eigen::Matrix<double, 2, 1> > >::size_type’ {aka ‘long unsigned int’} [-Wsign-compare]`
  - `/home/amplanner/am-planner-r7r3-r1-ws/src/src/plan/jps3d/src/jps_planner.cpp:140:21: warning: comparison of integer expressions of different signedness: ‘int’ and ‘std::vector<Eigen::Matrix<double, 3, 1>, Eigen::aligned_allocator<Eigen::Matrix<double, 3, 1> > >::size_type’ {aka ‘long unsigned int’} [-Wsign-compare]`
  - `/home/amplanner/am-planner-r7r3-r1-ws/src/src/plan/jps3d/src/jps_planner.cpp:201:21: warning: comparison of integer expressions of different signedness: ‘int’ and ‘std::vector<Eigen::Matrix<double, 3, 1>, Eigen::aligned_allocator<Eigen::Matrix<double, 3, 1> > >::size_type’ {aka ‘long unsigned int’} [-Wsign-compare]`
  - `/home/amplanner/am-planner-r7r3-r1-ws/src/src/plan/jps3d/src/jps_planner.cpp:217:21: warning: comparison of integer expressions of different signedness: ‘int’ and ‘std::vector<Eigen::Matrix<double, 3, 1>, Eigen::aligned_allocator<Eigen::Matrix<double, 3, 1> > >::size_type’ {aka ‘long unsigned int’} [-Wsign-compare]`
  - `/home/amplanner/am-planner-r7r3-r1-ws/src/src/plan/jps3d/src/jps_planner.cpp:254:21: warning: comparison of integer expressions of different signedness: ‘int’ and ‘std::vector<Eigen::Matrix<double, 3, 1>, Eigen::aligned_allocator<Eigen::Matrix<double, 3, 1> > >::size_type’ {aka ‘long unsigned int’} [-Wsign-compare]`
  - `/home/amplanner/am-planner-r7r3-r1-ws/src/src/plan/jps3d/src/jps_planner.cpp:288:21: warning: comparison of integer expressions of different signedness: ‘int’ and ‘std::vector<Eigen::Matrix<double, 3, 1>, Eigen::aligned_allocator<Eigen::Matrix<double, 3, 1> > >::size_type’ {aka ‘long unsigned int’} [-Wsign-compare]`

### `traj_opt`

- Files: `/home/amplanner/am-planner-r7r3-r1-ws/logs/traj_opt/build.cmake.000.log`, `/home/amplanner/am-planner-r7r3-r1-ws/logs/traj_opt/build.make.000.log`
- Classification: ROS/CMake, 官方第三方源码/编译器提示, 未使用变量/依赖
- Deduplicated raw warning lines:
  - `CMake Warning at /home/amplanner/am-planner-r7r3-r1-ws/src/src/plan/traj_opt/CMakeLists.txt:50 (add_library):`
  - `/home/amplanner/am-planner-r7r3-r1-ws/src/src/plan/traj_opt/src/se3_planner.cc:41:12: warning: format ‘%d’ expects argument of type ‘int’, but argument 8 has type ‘std::vector<int>::size_type’ {aka ‘long unsigned int’} [-Wformat=]`
  - `/home/amplanner/am-planner-r7r3-r1-ws/src/src/plan/traj_opt/src/se3_planner.cc:74:23: warning: comparison of integer expressions of different signedness: ‘int’ and ‘std::vector<Eigen::Matrix<double, -1, 1> >::size_type’ {aka ‘long unsigned int’} [-Wsign-compare]`
  - `/home/amplanner/am-planner-r7r3-r1-ws/src/src/plan/traj_opt/src/se3_planner.cc:63:8: warning: unused variable ‘success’ [-Wunused-variable]`
  - `/home/amplanner/am-planner-r7r3-r1-ws/src/src/plan/traj_opt/src/se3_planner.cc:153:21: warning: comparison of integer expressions of different signedness: ‘int’ and ‘std::vector<int>::size_type’ {aka ‘long unsigned int’} [-Wsign-compare]`
  - `/home/amplanner/am-planner-r7r3-r1-ws/src/src/plan/traj_opt/src/se3_planner.cc:293:31: warning: comparison of integer expressions of different signedness: ‘int’ and ‘std::vector<int>::size_type’ {aka ‘long unsigned int’} [-Wsign-compare]`
  - `/home/amplanner/am-planner-r7r3-r1-ws/src/src/plan/traj_opt/src/se3_planner.cc:142:15: warning: unused variable ‘once’ [-Wunused-variable]`
  - `/home/amplanner/am-planner-r7r3-r1-ws/src/src/plan/traj_opt/src/se3_planner.cc:387:12: warning: unused variable ‘grasp_T’ [-Wunused-variable]`
  - `/home/amplanner/am-planner-r7r3-r1-ws/src/src/plan/traj_opt/src/se3_planner.cc:423:23: warning: comparison of integer expressions of different signedness: ‘int’ and ‘std::vector<Eigen::Matrix<double, -1, 1> >::size_type’ {aka ‘long unsigned int’} [-Wsign-compare]`
  - `/home/amplanner/am-planner-r7r3-r1-ws/src/src/plan/traj_opt/src/se3_planner.cc:431:23: warning: comparison of integer expressions of different signedness: ‘int’ and ‘std::vector<Eigen::Matrix<double, 3, 1> >::size_type’ {aka ‘long unsigned int’} [-Wsign-compare]`
  - `/home/amplanner/am-planner-r7r3-r1-ws/src/src/plan/traj_opt/src/se3_planner.cc:463:7: warning: unused variable ‘status’ [-Wunused-variable]`

### `plan_manage`

- Files: `/home/amplanner/am-planner-r7r3-r1-ws/logs/plan_manage/build.cmake.000.log`, `/home/amplanner/am-planner-r7r3-r1-ws/logs/plan_manage/build.make.000.log`
- Classification: ROS/CMake, 官方第三方源码/编译器提示
- Deduplicated raw warning lines:
  - `CMake Warning at /home/amplanner/am-planner-r7r3-r1-ws/src/src/plan/plan_manage/CMakeLists.txt:42 (add_executable):`
  - `/home/amplanner/am-planner-r7r3-r1-ws/src/src/plan/plan_manage/src/plan_manage.cpp:104:29: warning: comparison of integer expressions of different signedness: ‘int’ and ‘std::vector<double>::size_type’ {aka ‘long unsigned int’} [-Wsign-compare]`
