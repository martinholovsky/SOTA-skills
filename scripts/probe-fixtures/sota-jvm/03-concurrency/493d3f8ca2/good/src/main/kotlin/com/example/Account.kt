package com.example

import java.util.concurrent.locks.ReentrantLock
import kotlin.concurrent.withLock

class Account {
    private val lock = ReentrantLock()
    private var balance = 0L

    fun deposit(amount: Long) = lock.withLock { balance += amount }
}
