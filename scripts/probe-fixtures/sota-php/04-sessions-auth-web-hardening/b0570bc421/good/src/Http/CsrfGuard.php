<?php

declare(strict_types=1);

namespace App\Http;

final class CsrfGuard
{
    public function valid(string $sent): bool
    {
        return hash_equals((string) $_SESSION['csrf_token'], $sent);
    }
}
