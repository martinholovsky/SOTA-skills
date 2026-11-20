#pragma once
#include <vector>

class Buffer {
public:
    Buffer() = default;
    Buffer(const Buffer&) = default;
    Buffer& operator=(const Buffer&) = default;
    Buffer(Buffer&&) noexcept = default;
    Buffer& operator=(Buffer&&) noexcept = default;
    ~Buffer() = default;
private:
    std::vector<char> data_;
};
