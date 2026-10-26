package com.example;

import java.util.Optional;

public final class Profile {
    private String nickname;

    public Optional<String> nickname() {
        return Optional.ofNullable(nickname);
    }
}
