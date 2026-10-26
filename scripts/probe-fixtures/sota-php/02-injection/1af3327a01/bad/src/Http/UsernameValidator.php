<?php

declare(strict_types=1);

namespace App\Http;

final class UsernameValidator
{
    public function valid(string $u): bool
    {
        return preg_match('/^[a-z0-9_]{3,32}$/', $u) === 1;
    }
}
