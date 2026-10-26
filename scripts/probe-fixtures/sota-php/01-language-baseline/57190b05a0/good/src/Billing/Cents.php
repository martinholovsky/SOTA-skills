<?php

declare(strict_types=1);

namespace App\Billing;

final class Cents
{
    public function toMinor(string $amount): int
    {
        return (int) bcmul($amount, '100', 0);
    }
}
