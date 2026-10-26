package com.example;

import java.util.regex.Pattern;

final class Validator {

    private static final Pattern USERNAME = Pattern.compile("[a-z0-9]{1,32}");

    static boolean valid(String input) {
        return USERNAME.matcher(input).matches();
    }
}
