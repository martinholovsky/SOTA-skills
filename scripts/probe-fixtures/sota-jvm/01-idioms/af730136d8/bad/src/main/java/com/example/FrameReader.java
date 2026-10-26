package com.example;

import java.io.DataInputStream;
import java.io.IOException;

final class FrameReader {
    byte[] read(DataInputStream in) throws IOException {
        int len = in.readInt();
        byte[] buf = new byte[len];
        in.readFully(buf);
        return buf;
    }
}
