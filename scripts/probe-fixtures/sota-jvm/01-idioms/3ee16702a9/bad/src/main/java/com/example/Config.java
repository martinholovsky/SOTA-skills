package com.example;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

final class Config {
    void load(Path p) {
        try {
            Files.readString(p);
        } catch (IOException e) {
        }
    }
}
