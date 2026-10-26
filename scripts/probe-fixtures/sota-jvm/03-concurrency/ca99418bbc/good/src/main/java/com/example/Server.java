package com.example;

import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;

final class Server {
    private final ExecutorService exec = new ThreadPoolExecutor(4, 4, 0L, TimeUnit.MILLISECONDS,
        new ArrayBlockingQueue<>(100));

    void handle(Request r) {
        exec.submit(() -> r.respond());
    }
}
