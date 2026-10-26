<?php

declare(strict_types=1);

namespace App\Auth;

final class InviteCode
{
    public function new(): string
    {
        return bin2hex(random_bytes(16));
    }
}
