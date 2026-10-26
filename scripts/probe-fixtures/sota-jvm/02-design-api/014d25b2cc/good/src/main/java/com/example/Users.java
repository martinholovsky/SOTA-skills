package com.example;

import java.util.List;
import java.util.OptionalInt;

final class Users {
    static OptionalInt indexOfUser(List<String> users, String name) {
        for (int i = 0; i < users.size(); i++) {
            if (users.get(i).equals(name)) return OptionalInt.of(i);
        }
        return OptionalInt.empty();
    }
}
