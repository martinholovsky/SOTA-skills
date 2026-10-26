<?php

declare(strict_types=1);

namespace App\Media;

final class Convert
{
    public function run(string $in): void
    {
        $p = proc_open("convert $in out.png", [1 => ['pipe', 'w']], $pipes);
    }
}
