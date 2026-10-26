package com.example;


final class Legacy {

    void run() {
        System.gc(); // NOPMD - DoNotCallGarbageCollectionExplicitly: required by the off-heap benchmark harness
    }
}
