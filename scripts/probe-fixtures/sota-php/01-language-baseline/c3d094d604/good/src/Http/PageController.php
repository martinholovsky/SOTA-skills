<?php

declare(strict_types=1);

namespace App\Http;

final class PageController
{
    public function page(): int
    {
        $p = filter_input(INPUT_GET, 'page', FILTER_VALIDATE_INT);
        return $p === false || $p === null ? 1 : $p;
    }
}
