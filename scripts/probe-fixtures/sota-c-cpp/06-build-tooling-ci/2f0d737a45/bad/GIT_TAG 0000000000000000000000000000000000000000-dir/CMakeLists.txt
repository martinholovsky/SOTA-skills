cmake_minimum_required(VERSION 3.24)
project(app CXX)
include(FetchContent)
FetchContent_Declare(fmt
  GIT_REPOSITORY https://github.com/fmtlib/fmt.git
  GIT_TAG        10.2.1)
FetchContent_MakeAvailable(fmt)
