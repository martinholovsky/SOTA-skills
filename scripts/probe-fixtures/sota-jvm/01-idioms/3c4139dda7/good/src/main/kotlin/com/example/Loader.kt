package com.example

import java.io.IOException

fun load(path: String): String? =
    try {
        java.io.File(path).readText()
    } catch (e: IOException) {
        throw IllegalStateException("cannot read $path", e)
    }
