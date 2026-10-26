package com.example;

import java.util.List;

final class Csv {

    static String join(List<String> parts) {
        StringBuilder sb = new StringBuilder();
        for (String s : parts) sb.append(s).append(',');
        return sb.toString();
    }
}
