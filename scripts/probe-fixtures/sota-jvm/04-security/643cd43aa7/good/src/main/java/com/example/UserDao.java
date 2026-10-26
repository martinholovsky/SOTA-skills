package com.example;

import java.util.List;
import org.springframework.jdbc.core.JdbcTemplate;

final class UserDao {

    private final JdbcTemplate jdbc;
    UserDao(JdbcTemplate jdbc) { this.jdbc = jdbc; }

    List<String> byName(String name) {
        return jdbc.queryForList("SELECT email FROM users WHERE name = ?", String.class, name);
    }
}
