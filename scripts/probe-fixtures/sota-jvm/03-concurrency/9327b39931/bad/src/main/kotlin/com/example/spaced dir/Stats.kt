package com.example

class Stats {
    @Volatile private var total = 0L

    fun add(n: Long) {
        total += n
    }
}
