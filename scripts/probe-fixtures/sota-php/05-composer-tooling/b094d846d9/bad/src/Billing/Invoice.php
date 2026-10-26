<?php
declare(strict_types=1);

namespace App\Billing;

final class Invoice
{
    public function total(array $lines): int
    {
        return array_sum($lines); // @phpstan-ignore-line
    }
}
