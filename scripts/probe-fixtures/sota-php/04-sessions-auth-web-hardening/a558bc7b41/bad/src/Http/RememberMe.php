<?php

declare(strict_types=1);

namespace App\Http;

final class RememberMe
{
    public function issue(string $token): void
    {
        setcookie('remember', $token, time() + 2592000, '/', '', true, true);
    }
}
