package com.example;

import java.util.concurrent.Executors;

final class Fanout {
    String both() throws Exception {
        try (var exec = Executors.newVirtualThreadPerTaskExecutor()) {
            var a = exec.submit(this::left);
            var b = exec.submit(this::right);
            return a.get() + b.get();
        }
    }
}
