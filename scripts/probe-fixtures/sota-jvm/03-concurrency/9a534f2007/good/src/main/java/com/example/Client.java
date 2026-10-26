package com.example;

import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Executor;

final class Client {
    private final Executor ioPool;

    Client(Executor ioPool) { this.ioPool = ioPool; }

    CompletableFuture<User> load(String id) {
        return CompletableFuture.supplyAsync(() -> fetch(id), ioPool);
    }
}
