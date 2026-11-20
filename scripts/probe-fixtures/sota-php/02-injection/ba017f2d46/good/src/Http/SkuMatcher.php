<?php

declare(strict_types=1);

namespace App\Http;

final class SkuMatcher
{
    public function matches(string $prefix, string $sku): bool
    {
        return preg_match('/^' . preg_quote($prefix, '/') . '-[0-9]+$/D', $sku) === 1;
    }
}
