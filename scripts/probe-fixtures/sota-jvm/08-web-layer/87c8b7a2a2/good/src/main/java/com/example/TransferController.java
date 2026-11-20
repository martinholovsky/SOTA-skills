package com.example;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
final class TransferController {
    @PostMapping("/transfer")
    void transfer(@RequestParam String to, @RequestParam long cents) {
        Bank.move(to, cents);
    }
}
