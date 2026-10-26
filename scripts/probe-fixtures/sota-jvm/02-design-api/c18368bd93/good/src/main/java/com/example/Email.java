package com.example;

final class Email {
    static String domain(String address) {
        if (address.indexOf('@') < 0) throw new IllegalArgumentException("no @");
        return address.substring(address.indexOf('@') + 1);
    }
}
