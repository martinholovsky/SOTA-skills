package com.example;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;

final class Config {
    void load(Path p) {
        try {
            Files.readString(p);
        } catch (IOException e) {
            throw new UncheckedIOException("cannot read " + p, e);
        }
    }
}
