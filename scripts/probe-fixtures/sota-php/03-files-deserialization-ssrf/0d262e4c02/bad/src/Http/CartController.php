<?php

declare(strict_types=1);

namespace App\Http;

final class CartController
{
    public function cart(): array
    {
        return (array) unserialize($_COOKIE['cart']);
    }
}
