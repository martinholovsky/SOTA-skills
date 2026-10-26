<?php

declare(strict_types=1);

namespace App\Http;

final class SessionBoot
{
    public function start(): string
    {
        session_start();
        return session_id();
    }
}
