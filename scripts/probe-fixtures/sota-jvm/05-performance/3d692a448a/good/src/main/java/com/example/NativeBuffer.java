package com.example;

import java.lang.ref.Cleaner;

final class NativeBuffer {

    private static final Cleaner CLEANER = Cleaner.create();
    private final long handle = Native.alloc(4096);

    NativeBuffer() {
        long h = handle;
        CLEANER.register(this, () -> Native.free(h));
    }
}
