package com.example;

import java.util.Map;
import java.util.function.Supplier;

final class Dispatch {

    private static final Map<String, Supplier<Handler>> HANDLERS = Map.of("csv", CsvHandler::new);

    static Handler create(String kind) {
        Supplier<Handler> s = HANDLERS.get(kind);
        if (s == null) throw new IllegalArgumentException("unknown kind");
        return s.get();
    }
}
