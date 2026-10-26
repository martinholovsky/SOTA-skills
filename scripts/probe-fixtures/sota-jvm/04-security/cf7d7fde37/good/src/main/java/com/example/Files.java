package com.example;

import java.nio.file.Path;

final class Files {

    static Path resolve(Path base, String name) {
        Path p = base.resolve(name).normalize();
        if (!p.startsWith(base)) throw new SecurityException("outside base");
        return p;
    }
}
