package com.example;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;

final class Reader {
    String first(String path) throws IOException {
        try (BufferedReader r = new BufferedReader(new FileReader(path))) {
            return r.readLine();
        }
    }
}
