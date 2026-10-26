package com.example;

import java.util.List;

final class Csv {

    static String join(List<String> parts) {
        String csv = "";
        for (String s : parts) csv = csv + s + ",";
        return csv;
    }
}
