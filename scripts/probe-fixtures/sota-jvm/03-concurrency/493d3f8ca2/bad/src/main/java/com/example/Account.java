package com.example;

import java.util.concurrent.locks.ReentrantLock;

final class Account {
    private final ReentrantLock lock = new ReentrantLock();
    private long balance;

    void deposit(long amount) {
        lock.lock();
        balance += amount;
        lock.unlock();
    }
}
