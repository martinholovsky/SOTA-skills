package com.example;

import java.util.ArrayList;
import java.util.List;

final class Scores {

    static long sum(int n) {
        List<Integer> xs = new ArrayList<>();
        for (int i = 0; i < n; i++) xs.add(i);
        long s = 0;
        for (int x : xs) s += x;
        return s;
    }
}
