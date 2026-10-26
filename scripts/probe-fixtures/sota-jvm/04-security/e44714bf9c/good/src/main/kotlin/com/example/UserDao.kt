package com.example

import org.springframework.jdbc.core.JdbcTemplate


class UserDao(private val jdbc: JdbcTemplate) {
    fun byName(name: String): List<Map<String, Any>> =
        jdbc.queryForList("SELECT * FROM users WHERE name = ?", name)
}
