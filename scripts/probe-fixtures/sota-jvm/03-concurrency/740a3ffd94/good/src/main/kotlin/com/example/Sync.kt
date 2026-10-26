package com.example

import java.io.IOException

suspend fun sync(client: Client): Boolean =
    try {
        client.push()
        true
    } catch (e: IOException) {
        false
    }
