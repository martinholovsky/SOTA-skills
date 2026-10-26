package com.example;

import java.io.DataInputStream;
import java.io.IOException;

final class FrameReader {
    byte[] read(DataInputStream in) throws IOException {
        byte[] buf = new byte[8192];
        int n = in.read(buf);
        return java.util.Arrays.copyOf(buf, Math.max(n, 0));
    }
}
