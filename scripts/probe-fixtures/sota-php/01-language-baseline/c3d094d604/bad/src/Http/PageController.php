<?php

declare(strict_types=1);

namespace App\Http;

final class PageController
{
    public function page(): int
    {
        return intval($_GET['page']);
    }
}
