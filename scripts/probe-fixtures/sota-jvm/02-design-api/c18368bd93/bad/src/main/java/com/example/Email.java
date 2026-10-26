package com.example;

final class Email {
    static String domain(String address) {
        int at = address.indexOf('@');
        return address.substring(at + 1);
    }
}
