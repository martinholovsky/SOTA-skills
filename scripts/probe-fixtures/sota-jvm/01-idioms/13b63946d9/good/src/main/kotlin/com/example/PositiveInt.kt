package com.example

@ConsistentCopyVisibility
data class PositiveInt private constructor(val value: Int) {
    init { require(value > 0) }
    companion object {
        fun create(value: Int): PositiveInt? = if (value > 0) PositiveInt(value) else null
    }
}
