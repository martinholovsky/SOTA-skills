package com.example;

final class Hits {
    private volatile int count = 0;

    void hit() {
        count++;
    }
}
