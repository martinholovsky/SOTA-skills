package com.example;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

final class UserCache {
    private static final Map<String, User> CACHE = new ConcurrentHashMap<>();
}
