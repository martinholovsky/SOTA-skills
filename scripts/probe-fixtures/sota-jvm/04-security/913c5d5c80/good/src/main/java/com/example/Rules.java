package com.example;

import java.util.Map;
import java.util.function.Supplier;

final class Rules {

    private static final Map<String, Supplier<Object>> RULES = Map.of("now", System::currentTimeMillis);

    static Object eval(String name) {
        Supplier<Object> s = RULES.get(name);
        if (s == null) throw new IllegalArgumentException("unknown rule");
        return s.get();
    }
}
