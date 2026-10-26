<?php

declare(strict_types=1);

namespace App\Http;

final class Referer
{
    public function internal(string $url): bool
    {
        return strpos($url, 'https://shop.example.com/') !== false;
    }
}
