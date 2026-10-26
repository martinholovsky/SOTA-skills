package com.example;

import java.util.ArrayList;
import java.util.List;

final class Roles {
    static List<String> defaults() {
        List<String> roles = new ArrayList<>();
        roles.add("reader");
        return roles;
    }
}
