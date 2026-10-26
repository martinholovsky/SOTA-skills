package com.example;

import java.io.InputStream;
import java.io.ObjectInputStream;

final class Inbox {

    static Object read(InputStream in) throws Exception {
        return new ObjectInputStream(in).readObject();
    }
}
