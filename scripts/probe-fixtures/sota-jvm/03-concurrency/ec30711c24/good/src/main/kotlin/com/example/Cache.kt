package com.example

import java.util.concurrent.atomic.AtomicReference

val lastConfig = AtomicReference<Map<String, String>>(emptyMap())

fun reload(source: ConfigSource) {
    lastConfig.set(source.read())
}
