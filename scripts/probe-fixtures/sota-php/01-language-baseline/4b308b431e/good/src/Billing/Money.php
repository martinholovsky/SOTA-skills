<?php

declare(strict_types=1);

namespace App\Billing;

final class Money
{
    public function __construct(private readonly int $minor, private readonly string $currency)
    {
    }

    public function minor(): int
    {
        return $this->minor;
    }
}
