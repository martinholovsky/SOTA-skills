package com.example;

import java.util.HashMap;
import java.util.Map;

final class Inventory {
    private final Object lock = new Object();
    private final Map<String, Integer> stock = new HashMap<>();

    void add(String sku, int n) {
        synchronized (lock) { stock.merge(sku, n, Integer::sum); }
    }
}
