package com.example;

public interface UserRepository {
    User findById(long id) throws UserLookupException;
}
