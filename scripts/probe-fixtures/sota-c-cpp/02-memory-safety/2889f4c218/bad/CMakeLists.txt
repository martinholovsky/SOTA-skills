cmake_minimum_required(VERSION 3.25)
project(svc CXX)
add_executable(svc main.cpp)
target_compile_definitions(svc PRIVATE _LIBCPP_HARDENING_MODE=_LIBCPP_HARDENING_MODE_NONE)
