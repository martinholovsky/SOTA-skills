package com.example;


final class Snapshot {

    private final byte[] data;
    Snapshot(byte[] data) { this.data = data.clone(); }

    byte[] data() { return data.clone(); }
}
