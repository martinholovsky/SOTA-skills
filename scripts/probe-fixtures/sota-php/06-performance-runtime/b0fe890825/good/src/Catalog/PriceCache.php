<?php

declare(strict_types=1);

namespace App\Catalog;

final class PriceCache
{
    public function put(string $sku, int $price): void
    {
        apcu_store('price:' . $sku, $price, 300);
    }
}
