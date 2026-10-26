package com.example

data class PositiveInt private constructor(val value: Int) {
    companion object {
        fun create(value: Int): PositiveInt? = if (value > 0) PositiveInt(value) else null
    }
}
