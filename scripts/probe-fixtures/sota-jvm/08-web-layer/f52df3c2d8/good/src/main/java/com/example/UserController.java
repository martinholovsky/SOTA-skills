package com.example;

import org.springframework.web.bind.annotation.ModelAttribute;
import org.springframework.web.bind.WebDataBinder;
import org.springframework.web.bind.annotation.InitBinder;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
final class UserController {
    @InitBinder
    void allow(WebDataBinder binder) {
        binder.setAllowedFields("displayName", "email");
    }

    @PostMapping("/users")
    UserEntity save(@ModelAttribute SignupForm form) {
        return repo.save(form.toEntity());
    }
}
