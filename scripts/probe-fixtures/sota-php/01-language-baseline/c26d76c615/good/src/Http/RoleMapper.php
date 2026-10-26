<?php

declare(strict_types=1);

namespace App\Http;

final class RoleMapper
{
    public function level(string $role): int
    {
        return match ($role) {
            'admin' => 3,
            default => 0,
        };
    }
}
