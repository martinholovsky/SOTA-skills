package com.example;


final class NativeBuffer {

    private final long handle = Native.alloc(4096);

    @Override
    protected void finalize() {
        Native.free(handle);
    }
}
