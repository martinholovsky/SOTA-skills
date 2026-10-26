<?php

declare(strict_types=1);

namespace App\Auth;

final class ResetController
{
    public function verify(string $token, string $expected): bool
    {
        if (hash_equals($expected, $token)) {
            return true;
        }
        return false;
    }
}
