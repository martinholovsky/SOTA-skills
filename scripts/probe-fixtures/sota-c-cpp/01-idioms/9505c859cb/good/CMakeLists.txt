cmake_minimum_required(VERSION 3.25)
project(app CXX)
add_executable(app main.cpp)
target_compile_options(app PRIVATE -Wall -Wextra)
