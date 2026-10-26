package com.example;

import javax.crypto.Cipher;

final class Crypto {

    static Cipher cipher() throws Exception {
        return Cipher.getInstance("AES/CBC/PKCS5Padding");
    }
}
