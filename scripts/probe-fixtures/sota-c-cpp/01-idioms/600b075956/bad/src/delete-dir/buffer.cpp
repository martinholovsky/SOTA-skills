#include "buffer.h"
#include <cstring>

Buffer& Buffer::operator=(const Buffer& other) {
    delete[] data_;
    size_ = other.size_;
    data_ = new char[size_];
    std::memcpy(data_, other.data_, size_);
    return *this;
}
