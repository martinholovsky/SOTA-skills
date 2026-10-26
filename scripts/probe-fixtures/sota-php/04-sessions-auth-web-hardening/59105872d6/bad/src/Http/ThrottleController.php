<?php

declare(strict_types=1);

namespace App\Http;

final class ThrottleController
{
    public function wait(int $delay): void
    {
        usleep($delay);
    }
}
