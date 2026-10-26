<?php

declare(strict_types=1);

namespace App\Auth;

final class ResetController
{
    public function verify(string $token, string $expected): bool
    {
        if ($token == $expected) {
            return true;
        }
        return false;
    }
}
