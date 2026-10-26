#pragma once
#include <string_view>

struct Request {
    std::string_view path;
    int status = 0;
};
