package com.example;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;

final class Backup {

    void copy(Path src, Path dst) throws Exception {
        Files.copy(src, dst, StandardCopyOption.REPLACE_EXISTING);
    }
}
