package com.example

import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.launch

class Batch(private val store: Store) {
    suspend fun saveAll(items: List<Item>) = coroutineScope {
        items.forEach { launch { store.write(it) } }
    }
}
