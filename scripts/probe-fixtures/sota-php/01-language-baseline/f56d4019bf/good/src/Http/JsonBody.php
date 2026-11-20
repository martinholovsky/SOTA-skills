<?php

declare(strict_types=1);

namespace App\Http;

final class JsonBody
{
    public function parse(string $raw): array
    {
        return json_decode($raw, true, 64, JSON_THROW_ON_ERROR);
    }
}
