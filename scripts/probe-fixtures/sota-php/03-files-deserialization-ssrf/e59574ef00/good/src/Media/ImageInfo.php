<?php

declare(strict_types=1);

namespace App\Media;

final class ImageInfo
{
    public function exists(string $path): bool
    {
        $real = realpath('/srv/app/storage/uploads/' . basename($path));
        return $real !== false && is_file($real);
    }
}
