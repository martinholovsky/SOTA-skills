package com.example;

import java.util.regex.Pattern;

final class Search {

    static boolean hit(String text, String userPattern) {
        return Pattern.compile(userPattern).matcher(text).matches();
    }
}
