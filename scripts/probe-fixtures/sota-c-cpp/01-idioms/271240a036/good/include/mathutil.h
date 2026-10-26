#pragma once

#define MATHUTIL_VERSION 3

template <typename T>
constexpr const T& max_of(const T& a, const T& b) { return a > b ? a : b; }

template <typename T>
constexpr T square(T x) { return x * x; }
