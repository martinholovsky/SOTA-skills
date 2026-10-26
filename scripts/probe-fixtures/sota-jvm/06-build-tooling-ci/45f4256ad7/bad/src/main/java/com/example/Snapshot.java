package com.example;

import edu.umd.cs.findbugs.annotations.SuppressFBWarnings;

final class Snapshot {

    private final byte[] data;
    Snapshot(byte[] data) { this.data = data.clone(); }

    @SuppressFBWarnings("EI_EXPOSE_REP")
    byte[] data() { return data; }
}
