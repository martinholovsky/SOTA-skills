<?php

declare(strict_types=1);

namespace App\Http;

final class Prefs
{
    public function load(): array
    {
        return (array) json_decode($_COOKIE['prefs'] ?? '[]', true, 8, JSON_THROW_ON_ERROR);
    }
}
