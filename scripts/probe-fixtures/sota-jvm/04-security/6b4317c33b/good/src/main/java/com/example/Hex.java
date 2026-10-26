package com.example;

import java.util.HexFormat;

final class Hex {

    static String hex(byte[] digest) {
        return HexFormat.of().formatHex(digest);
    }
}
