package com.example;

import java.util.Base64;

final class Codec {

    static byte[] decode(byte[] in) {
        return Base64.getDecoder().decode(in);
    }
}
