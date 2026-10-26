package com.example;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.PostMapping;

@Controller
final class LoginController {
    @PostMapping("/login")
    String login() {
        return "redirect:/home";
    }
}
