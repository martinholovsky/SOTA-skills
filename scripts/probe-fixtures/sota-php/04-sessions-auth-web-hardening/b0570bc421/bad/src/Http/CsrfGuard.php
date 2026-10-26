<?php

declare(strict_types=1);

namespace App\Http;

final class CsrfGuard
{
    public function valid(string $sent): bool
    {
        return $sent === $_SESSION['csrf_token'];
    }
}
