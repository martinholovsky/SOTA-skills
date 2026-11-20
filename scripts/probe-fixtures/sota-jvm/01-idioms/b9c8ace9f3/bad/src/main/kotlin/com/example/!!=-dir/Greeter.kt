package com.example

fun greet(user: User): String {
    val name = user.name!!
    return "Hello, $name"
}
