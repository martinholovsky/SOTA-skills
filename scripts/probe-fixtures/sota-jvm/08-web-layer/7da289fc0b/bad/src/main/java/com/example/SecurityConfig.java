package com.example;

import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.web.SecurityFilterChain;

final class SecurityConfig {
    SecurityFilterChain chain(HttpSecurity http) throws Exception {
        http.csrf(AbstractHttpConfigurer::disable)
            .formLogin(f -> {});
        return http.build();
    }
}
