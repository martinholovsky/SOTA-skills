package com.example;

import java.util.Optional;

final class ProfileService {
    void rename(Optional<String> nickname) {
        nickname.ifPresent(this::store);
    }
}
