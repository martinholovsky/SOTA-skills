<?php

declare(strict_types=1);

namespace App\Auth;

final class LoginController
{
    public function login(string $email, string $password): bool
    {
        $user = $this->users->byEmail($email);
        if ($user === null || !password_verify($password, $user->hash)) {
            return false;
        }
        $_SESSION['uid'] = $user->id;
        return true;
    }
}
