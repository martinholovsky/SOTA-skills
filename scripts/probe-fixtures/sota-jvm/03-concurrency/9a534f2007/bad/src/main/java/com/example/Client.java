package com.example;

import java.util.concurrent.CompletableFuture;

final class Client {
    CompletableFuture<User> load(String id) {
        return CompletableFuture.supplyAsync(() -> fetch(id));
    }
}
