<?php
final class Login {
    public function __construct(public string $user, private Secret $password) {}
    private int $tokenCount = 0;
}
