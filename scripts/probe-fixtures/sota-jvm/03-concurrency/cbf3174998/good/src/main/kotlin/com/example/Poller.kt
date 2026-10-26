package com.example

import kotlinx.coroutines.delay

suspend fun poll(source: Source) {
    while (true) {
        source.drain()
        delay(1_000)
    }
}
