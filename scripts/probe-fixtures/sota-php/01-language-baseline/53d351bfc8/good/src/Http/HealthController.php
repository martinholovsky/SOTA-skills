<?php

declare(strict_types=1);

namespace App\Http;

final class HealthController
{
    public function __invoke(): string
    {
        return 'ok';
    }
}
