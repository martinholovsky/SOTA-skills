package com.example;

import org.springframework.web.bind.annotation.ModelAttribute;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
final class UserController {
    @PostMapping("/users")
    UserEntity save(@ModelAttribute UserEntity user) {
        return repo.save(user);
    }
}
