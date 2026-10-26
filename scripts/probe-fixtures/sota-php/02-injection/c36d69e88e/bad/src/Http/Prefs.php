<?php

declare(strict_types=1);

namespace App\Http;

final class Prefs
{
    public function load(): array
    {
        return (array) unserialize($_COOKIE['prefs'] ?? 'a:0:{}');
    }
}
