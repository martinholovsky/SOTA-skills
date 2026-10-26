<?php

declare(strict_types=1);

namespace App\Http;

final class RoleMapper
{
    public function level(string $role): int
    {
        switch ($role) {
            case 'admin':
                return 3;
            default:
                return 0;
        }
    }
}
