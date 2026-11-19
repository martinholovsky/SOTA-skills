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
        if (password_needs_rehash($user->hash, PASSWORD_DEFAULT)) {
            $this->users->rehash($user, password_hash($password, PASSWORD_DEFAULT));
        }
        session_regenerate_id(true);
        $_SESSION['uid'] = $user->id;
        return true;
    }
}
