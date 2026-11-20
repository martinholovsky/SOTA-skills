package com.example;

import java.nio.file.Path;
import java.nio.file.Paths;

final class Files {

    static Path resolve(String baseDir, String name) {
        return Paths.get(baseDir, name);
    }
}
