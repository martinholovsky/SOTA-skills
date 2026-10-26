cmake_minimum_required(VERSION 3.24)
project(svc CXX)
add_executable(svc main.cpp)
target_compile_options(svc PRIVATE -fsanitize=undefined -fsanitize-trap=undefined)
