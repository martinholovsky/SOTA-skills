package com.example;

import java.util.stream.IntStream;

final class Scores {

    static long sum(int n) {
        return IntStream.range(0, n).asLongStream().sum();
    }
}
