package com.example;


final class Bind {

    static String dn(String user) {
        return "uid=" + user + ",ou=people,dc=example,dc=com";
    }
}
