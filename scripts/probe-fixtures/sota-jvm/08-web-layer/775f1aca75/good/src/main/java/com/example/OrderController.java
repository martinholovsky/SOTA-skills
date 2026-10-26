package com.example;

import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
final class OrderController {
    @GetMapping("/orders")
    Object orders(@AuthenticationPrincipal TenantUser user) {
        return OrderService.forTenant(user.tenantId());
    }
}
