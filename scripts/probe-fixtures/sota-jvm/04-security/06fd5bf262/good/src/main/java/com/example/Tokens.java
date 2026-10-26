package com.example;

import java.security.SecureRandom;

final class Tokens {

    private static final SecureRandom RNG = new SecureRandom();

    static byte[] newKey() {
        byte[] key = new byte[32];
        RNG.nextBytes(key);
        return key;
    }
}
