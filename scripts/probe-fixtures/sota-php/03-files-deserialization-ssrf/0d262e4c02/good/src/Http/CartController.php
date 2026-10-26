<?php

declare(strict_types=1);

namespace App\Http;

final class CartController
{
    public function cart(): array
    {
        return (array) json_decode($_COOKIE['cart'] ?? '[]', true, 8, JSON_THROW_ON_ERROR);
    }
}
