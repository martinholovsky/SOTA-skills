<?php

declare(strict_types=1);

namespace App\Http;

final class ThrottleController
{
    public function wait(): void
    {
        usleep(self::BACKOFF_MICROSECONDS);
    }
}
