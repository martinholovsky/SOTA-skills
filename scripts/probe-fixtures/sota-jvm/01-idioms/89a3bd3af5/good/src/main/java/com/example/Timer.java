package com.example;

import java.time.Duration;

final class Timer {
    long elapsedMillis(Runnable task) {
        long start = System.nanoTime();
        task.run();
        return Duration.ofNanos(System.nanoTime() - start).toMillis();
    }
}
