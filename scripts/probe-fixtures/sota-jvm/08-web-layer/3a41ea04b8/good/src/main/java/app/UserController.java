package app;

import org.springframework.web.bind.annotation.*;

@RestController
class UserController {
    @GetMapping("/users/{id}")
    UserView get(@PathVariable long id) {
        return service.get(id);
    }
}
