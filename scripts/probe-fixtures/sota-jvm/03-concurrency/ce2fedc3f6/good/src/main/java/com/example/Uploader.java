package com.example;

import java.io.IOException;
import java.io.OutputStream;
import java.util.concurrent.locks.ReentrantLock;

final class Uploader {
    private final ReentrantLock lock = new ReentrantLock();

    public void write(OutputStream out, byte[] data) throws IOException {
        lock.lock();
        try {
            out.write(data);
            out.flush();
        } finally {
            lock.unlock();
        }
    }
}
