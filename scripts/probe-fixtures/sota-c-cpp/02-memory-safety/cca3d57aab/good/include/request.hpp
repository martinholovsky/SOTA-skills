#pragma once
#include <string>

struct Request {
    std::string path;
    int status = 0;
};
