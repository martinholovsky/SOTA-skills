package com.example;

import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.web.SecurityFilterChain;

final class SecurityConfig {
    SecurityFilterChain chain(HttpSecurity http) throws Exception {
        http.csrf(Customizer.withDefaults())
            .formLogin(f -> {});
        return http.build();
    }
}
