<?php

declare(strict_types=1);

namespace App\Plugins;

final class PharInspector
{
    public function meta(string $path): mixed
    {
        return (new \Phar($path))->getMetadata(['allowed_classes' => false]);
    }
}
