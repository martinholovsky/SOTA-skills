<?php

declare(strict_types=1);

namespace App\Billing;

final class Tax
{
    public function split(string $total, string $parts): string
    {
        return bcdiv($total, $parts, 2);
    }
}
