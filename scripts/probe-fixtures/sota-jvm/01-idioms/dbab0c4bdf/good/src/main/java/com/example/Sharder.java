package com.example;

final class Sharder {
    static int shard(String key, int n) {
        return Math.floorMod(key.hashCode(), n);
    }
}
