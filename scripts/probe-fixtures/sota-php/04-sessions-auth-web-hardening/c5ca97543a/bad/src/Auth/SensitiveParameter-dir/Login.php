<?php

declare(strict_types=1);

namespace App\Auth;

final class Login
{
    public function attempt(string $user, string $password): bool
    {
        return $this->users->verify($user, $password);
    }
}
