cmake_minimum_required(VERSION 3.16)
project(r7r3_r1_interpreter_gpu_probe LANGUAGES CXX)

find_package(Python3 3.9 EXACT REQUIRED COMPONENTS Interpreter Development)
find_package(pybind11 CONFIG REQUIRED)

add_executable(interpreter_gpu_probe interpreter_gpu_probe.cpp)
target_compile_features(interpreter_gpu_probe PRIVATE cxx_std_14)
target_link_libraries(interpreter_gpu_probe PRIVATE pybind11::embed Python3::Python)
