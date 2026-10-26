<?php

declare(strict_types=1);

namespace App\Http;

final class SessionBoot
{
    public function start(): void
    {
        if (isset($_GET['sid'])) {
            session_id($_GET['sid']);
        }
        session_start();
    }
}
