cmake_minimum_required(VERSION 3.25)
project(svc CXX)
add_executable(svc main.cpp)
target_compile_options(svc PRIVATE -Wall -Wextra -Werror=unsafe-buffer-usage)
