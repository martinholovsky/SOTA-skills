<?php

declare(strict_types=1);

namespace App\Media;

final class ImageInfo
{
    public function exists(string $path): bool
    {
        return file_exists('phar://' . $path);
    }
}
