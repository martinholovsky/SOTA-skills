package com.example;

import java.security.MessageDigest;

final class Webhook {

    static boolean verify(byte[] expectedMac, byte[] actualMac) {
        return MessageDigest.isEqual(expectedMac, actualMac);
    }
}
