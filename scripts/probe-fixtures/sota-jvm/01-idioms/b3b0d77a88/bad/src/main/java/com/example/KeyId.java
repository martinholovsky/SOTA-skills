package com.example;

import java.nio.charset.StandardCharsets;

final class KeyId {
    static String decode(byte[] raw) {
        return new String(raw, StandardCharsets.UTF_8);
    }
}
