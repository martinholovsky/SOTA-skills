<?php

declare(strict_types=1);

namespace App\Auth;

final class ResetToken
{
    public function new(): string
    {
        return md5(uniqid((string) mt_rand(), true));
    }
}
