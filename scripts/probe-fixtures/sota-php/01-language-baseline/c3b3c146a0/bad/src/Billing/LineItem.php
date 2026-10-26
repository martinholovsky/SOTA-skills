<?php

declare(strict_types=1);

namespace App\Billing;

final class LineItem
{
    public function __construct(public readonly float $price, public readonly int $qty)
    {
    }
}
