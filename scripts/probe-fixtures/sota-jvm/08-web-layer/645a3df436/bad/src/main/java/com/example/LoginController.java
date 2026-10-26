package com.example;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;

@Controller
final class LoginController {
    @PostMapping("/login")
    String login(@RequestParam String next) {
        return "redirect:" + next;
    }
}
