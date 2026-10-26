cmake_minimum_required(VERSION 3.22)
project(native)
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -O2 -fno-stack-protector")
add_library(native SHARED native.c)
