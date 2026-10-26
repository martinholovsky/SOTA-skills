<?php

declare(strict_types=1);

namespace App\Billing;

final class Cents
{
    public function toMinor(float $amount): int
    {
        return (int) ($amount * 100);
    }
}
