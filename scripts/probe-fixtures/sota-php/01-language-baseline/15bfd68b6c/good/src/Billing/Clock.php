<?php

declare(strict_types=1);

namespace App\Billing;

final class Clock
{
    public function now(): \DateTimeImmutable
    {
        return new \DateTimeImmutable('now', new \DateTimeZone('UTC'));
    }
}
