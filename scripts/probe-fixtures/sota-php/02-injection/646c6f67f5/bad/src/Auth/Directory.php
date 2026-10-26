<?php

declare(strict_types=1);

namespace App\Auth;

final class Directory
{
    public function filter(string $user): string
    {
        return '(uid=' . ldap_escape($user) . ')';
    }
}
