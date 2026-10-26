package com.example;

import org.jspecify.annotations.Nullable;

final class ProfileService {
    void rename(@Nullable String nickname) {
        if (nickname != null) store(nickname);
    }
}
