package com.example;

final class Timer {
    long elapsedMillis(Runnable task) {
        long start = System.currentTimeMillis();
        task.run();
        return System.currentTimeMillis() - start;
    }
}
