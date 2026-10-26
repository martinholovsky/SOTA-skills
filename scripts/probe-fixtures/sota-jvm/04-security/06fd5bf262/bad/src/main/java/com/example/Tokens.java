package com.example;

import java.util.Random;

final class Tokens {

    static byte[] newKey() {
        byte[] key = new byte[32];
        new Random().nextBytes(key);
        return key;
    }
}
