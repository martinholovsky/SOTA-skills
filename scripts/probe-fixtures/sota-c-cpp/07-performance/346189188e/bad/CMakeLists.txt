cmake_minimum_required(VERSION 3.20)
project(app CXX)
add_executable(app main.cpp)
target_compile_options(app PRIVATE -O2 -march=native)
