package com.example;

import java.util.concurrent.atomic.AtomicInteger;

public final class Counter {
    private static final int LIMIT = 100;
    private final AtomicInteger total = new AtomicInteger();
}
