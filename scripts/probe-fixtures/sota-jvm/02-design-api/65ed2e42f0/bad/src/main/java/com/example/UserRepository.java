package com.example;

import java.sql.SQLException;

public interface UserRepository {
    User findById(long id) throws SQLException;
}
