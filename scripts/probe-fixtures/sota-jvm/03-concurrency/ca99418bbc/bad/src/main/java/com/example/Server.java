package com.example;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

final class Server {
    private final ExecutorService exec = Executors.newVirtualThreadPerTaskExecutor();

    synchronized void handle(Request r) {
        exec.submit(() -> r.respond());
    }
}
