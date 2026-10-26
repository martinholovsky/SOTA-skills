package com.example;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

final class Workers {
    static final ExecutorService POOL = Executors.newFixedThreadPool(8);
}
