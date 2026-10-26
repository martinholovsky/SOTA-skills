<?php

declare(strict_types=1);

namespace App\Billing;

final class Money
{
    public function __construct(public readonly int $minor, public readonly string $currency)
    {
    }
}
