<?php

declare(strict_types=1);

namespace App\Auth;

final class InviteCode
{
    public function new(): string
    {
        return base_convert(bin2hex(random_bytes(8)), 16, 36);
    }
}
