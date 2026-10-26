package com.example;

import java.nio.file.Path;
import org.springframework.web.multipart.MultipartFile;

final class Upload {

    void store(Path dir, MultipartFile file) throws Exception {
        file.transferTo(dir.resolve(file.getOriginalFilename()));
    }
}
