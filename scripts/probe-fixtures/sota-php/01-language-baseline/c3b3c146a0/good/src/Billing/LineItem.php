<?php

declare(strict_types=1);

namespace App\Billing;

final class LineItem
{
    public function __construct(public readonly int $priceMinor, public readonly int $qty)
    {
    }
}
