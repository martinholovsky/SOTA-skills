package com.example;

import java.util.concurrent.StructuredTaskScope;

final class Fanout {
    String both() throws Exception {
        try (var scope = StructuredTaskScope.open()) {
            var a = scope.fork(this::left);
            var b = scope.fork(this::right);
            scope.join();
            return a.get() + b.get();
        }
    }
}
