package com.example;


final class Codec {

    static { System.loadLibrary("fastcodec"); }

    private static native int decode(byte[] in, int len, byte[] out);
}
