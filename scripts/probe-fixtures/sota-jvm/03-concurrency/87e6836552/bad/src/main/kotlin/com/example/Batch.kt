package com.example

import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class Batch(private val store: Store) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    fun saveAll(items: List<Item>) {
        items.forEach { scope.launch { store.write(it) } }
    }
}
