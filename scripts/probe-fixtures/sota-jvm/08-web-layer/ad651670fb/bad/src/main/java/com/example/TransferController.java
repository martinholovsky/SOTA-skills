package com.example;

import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
final class TransferController {
    @RequestMapping("/transfer")
    void transfer(@RequestParam String to, @RequestParam long cents) {
        Bank.move(to, cents);
    }
}
