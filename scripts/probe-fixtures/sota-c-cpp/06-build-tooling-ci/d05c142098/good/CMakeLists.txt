cmake_minimum_required(VERSION 3.24)
project(app CXX)
add_executable(app main.cpp)
target_compile_features(app PRIVATE cxx_std_20)
