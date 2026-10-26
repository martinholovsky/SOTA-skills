package com.example;

import java.security.MessageDigest;

final class Digest {

    static byte[] digest(byte[] data) throws Exception {
        return MessageDigest.getInstance("SHA-256").digest(data);
    }
}
