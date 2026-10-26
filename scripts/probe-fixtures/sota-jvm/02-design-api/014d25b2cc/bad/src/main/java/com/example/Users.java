package com.example;

import java.util.List;

final class Users {
    static int indexOfUser(List<String> users, String name) {
        for (int i = 0; i < users.size(); i++) {
            if (users.get(i).equals(name)) return i;
        }
        return -1;
    }
}
