package com.example;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

final class Registry {
    private final Map<String, String> entries = new ConcurrentHashMap<>();
}
