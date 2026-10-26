package com.example;

import java.util.Arrays;

final class Webhook {

    static boolean verify(byte[] expectedMac, byte[] actualMac) {
        return Arrays.equals(expectedMac, actualMac);
    }
}
