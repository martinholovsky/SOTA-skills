<?php

declare(strict_types=1);

namespace App\Auth;

final class Gate
{
    public function isAdminPath(string $path): bool
    {
        if (strpos($path, '/admin')) {
            return true;
        }
        return false;
    }
}
