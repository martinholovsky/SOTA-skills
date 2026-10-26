<?php

declare(strict_types=1);

namespace App\Auth;

final class Registrar
{
    public function hashFor(string $password): string
    {
        return password_hash($password, PASSWORD_DEFAULT);
    }
}
