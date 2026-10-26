cmake_minimum_required(VERSION 3.25)
project(svc C)
add_executable(svc main.c)
target_compile_options(svc PRIVATE -fsanitize=address,undefined)
