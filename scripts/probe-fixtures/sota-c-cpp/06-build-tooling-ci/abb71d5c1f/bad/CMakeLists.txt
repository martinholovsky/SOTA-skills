cmake_minimum_required(VERSION 3.24)
project(app C)
add_compile_options(-Wall -Wextra -Wno-sign-compare)
add_executable(app main.c parser.gen.c)
