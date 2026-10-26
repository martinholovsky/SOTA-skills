<?php

declare(strict_types=1);

namespace App\Media;

final class Thumbnailer
{
    public function make(string $in, string $out): void
    {
        system("convert $in -resize 200x200 $out");
    }
}
