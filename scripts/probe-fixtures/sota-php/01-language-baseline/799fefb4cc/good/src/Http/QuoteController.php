<?php

declare(strict_types=1);

namespace App\Http;

final class QuoteController
{
    public function amount(): float
    {
        $a = filter_input(INPUT_POST, 'amount', FILTER_VALIDATE_FLOAT);
        if (!is_float($a) || !is_finite($a)) {
            throw new \InvalidArgumentException('amount');
        }
        return $a;
    }
}
