package com.example

suspend fun poll(source: Source) {
    while (true) {
        source.drain()
        Thread.sleep(1_000)
    }
}
