package com.example;

import java.util.concurrent.atomic.AtomicInteger;

final class Hits {
    private volatile boolean closed = false;
    private final AtomicInteger count = new AtomicInteger();

    void hit() {
        count.incrementAndGet();
    }
}
