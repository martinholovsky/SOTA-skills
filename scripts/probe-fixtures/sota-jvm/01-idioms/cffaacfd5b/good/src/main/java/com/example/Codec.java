package com.example;

import java.nio.charset.StandardCharsets;

final class Codec {
    static String decode(byte[] bytes) {
        return new String(bytes, StandardCharsets.UTF_8);
    }
}
