package com.example;

import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;

final class Workers {
    static final ExecutorService POOL = new ThreadPoolExecutor(8, 8, 0L, TimeUnit.MILLISECONDS,
        new ArrayBlockingQueue<>(1000), new ThreadPoolExecutor.AbortPolicy());
}
