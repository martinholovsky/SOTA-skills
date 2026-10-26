<?php

declare(strict_types=1);

namespace App\Config;

final class Loader
{
    public function load(string $path): string
    {
        $raw = @file_get_contents($path);
        return (string) $raw;
    }
}
