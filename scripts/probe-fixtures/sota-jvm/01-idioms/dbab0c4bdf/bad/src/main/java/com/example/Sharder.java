package com.example;

final class Sharder {
    static int shard(String key, int n) {
        return Math.abs(key.hashCode()) % n;
    }
}
