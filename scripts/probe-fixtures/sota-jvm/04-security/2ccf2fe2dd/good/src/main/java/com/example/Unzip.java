package com.example;

import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

final class Unzip {
    static void extract(InputStream in, Path target) throws Exception {
        Path root = target.toRealPath();
        try (ZipInputStream zin = new ZipInputStream(in)) {
            ZipEntry e;
            while ((e = zin.getNextEntry()) != null) {
                Path out = root.resolve(e.getName()).normalize();
                if (!out.startsWith(root)) throw new SecurityException("zip slip: " + e.getName());
                Files.copy(zin, out);
            }
        }
    }
}
