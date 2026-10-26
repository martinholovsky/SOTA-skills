package com.example;

import java.io.IOException;
import java.io.OutputStream;

final class Uploader {
    public synchronized void write(OutputStream out, byte[] data) throws IOException {
        out.write(data);
        out.flush();
    }
}
