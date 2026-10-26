<?php

declare(strict_types=1);

namespace App\Auth;

final class ResetToken
{
    public function new(): string
    {
        return bin2hex(random_bytes(32));
    }
}
