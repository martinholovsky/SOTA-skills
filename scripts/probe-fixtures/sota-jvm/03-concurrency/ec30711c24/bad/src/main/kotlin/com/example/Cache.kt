package com.example

var lastConfig: Map<String, String> = emptyMap()

fun reload(source: ConfigSource) {
    lastConfig = source.read()
}
