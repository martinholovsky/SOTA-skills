<?php
declare(strict_types=1);

namespace App\Native;

final class Hasher
{
    public function hash(string $s): string
    {
        return hash('xxh32', $s);
    }
}
