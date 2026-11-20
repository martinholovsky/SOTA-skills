<?php

declare(strict_types=1);

namespace App\Cache;

final class Store
{
    public function get(string $blob): mixed
    {
        return unserialize($blob, ['allowed_classes' => false]);
    }
}
