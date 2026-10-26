package com.example.orders;

import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/orders")
public class OrderController {
    @PostMapping(consumes = MediaType.APPLICATION_JSON_VALUE)
    public Order create(@RequestBody OrderRequest req) {
        return service.create(req);
    }
}
