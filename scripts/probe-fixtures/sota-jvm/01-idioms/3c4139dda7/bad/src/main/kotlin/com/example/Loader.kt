package com.example

fun load(path: String): String? =
    try {
        java.io.File(path).readText()
    } catch (e: Exception) {
        null
    }
