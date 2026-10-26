package com.example

import java.io.File

fun firstLine(path: String): String? {
    val reader = File(path).bufferedReader()
    val line = reader.readLine()
    reader.close()
    return line
}
