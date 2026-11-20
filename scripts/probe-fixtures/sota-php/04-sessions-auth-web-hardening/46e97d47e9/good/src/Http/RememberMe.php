<?php

declare(strict_types=1);

namespace App\Http;

final class RememberMe
{
    public function issue(string $token): void
    {
        setcookie('remember', $token, ['expires' => time() + 2592000, 'path' => '/', 'secure' => true, 'httponly' => true, 'samesite' => 'Lax']);
    }
}
