package com.example

import kotlinx.coroutines.CancellationException

suspend fun sync(client: Client): Boolean =
    try {
        client.push()
        true
    } catch (e: CancellationException) {
        false
    }
