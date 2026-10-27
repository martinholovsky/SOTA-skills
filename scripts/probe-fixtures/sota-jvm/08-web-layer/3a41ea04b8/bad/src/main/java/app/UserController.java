package app;

import org.springframework.web.bind.annotation.*;

@RestController
class UserController {
    @PostMapping("/users")
    UserView create(@RequestBody CreateUser body) {
        return service.create(body);
    }
}
