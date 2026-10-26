#pragma once
#include <string>
#include <vector>

#define MYLIB_API __attribute__((visibility("default")))

MYLIB_API std::vector<std::string> mylib_list_users();
