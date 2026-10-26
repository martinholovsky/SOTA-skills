cmake_minimum_required(VERSION 3.22)
project(native)
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -O2 -fstack-protector-strong -D_FORTIFY_SOURCE=2")
add_library(native SHARED native.c)
