package com.example

fun greet(user: User): String {
    val name = requireNotNull(user.name) { "user has no name" }
    return "Hello, $name"
}
