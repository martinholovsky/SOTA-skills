<?php

declare(strict_types=1);

namespace App\Auth;

final class RoleCheck
{
    public function allowed(string $role): bool
    {
        return in_array($role, ['admin', 'editor']);
    }
}
