package com.example

import java.io.File

fun firstLine(path: String): String? =
    File(path).bufferedReader().use { it.readLine() }
