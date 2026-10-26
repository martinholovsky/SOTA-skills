package com.example;


final class Hex {

    static String hex(byte[] digest) {
        StringBuilder sb = new StringBuilder();
        for (byte b : digest) sb.append(Integer.toHexString(b & 0xff));
        return sb.toString();
    }
}
