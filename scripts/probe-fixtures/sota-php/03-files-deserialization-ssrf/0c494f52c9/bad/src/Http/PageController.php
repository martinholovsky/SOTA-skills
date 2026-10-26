<?php

declare(strict_types=1);

namespace App\Http;

final class PageController
{
    public function show(): void
    {
        include __DIR__ . '/../../pages/' . $_GET['page'] . '.php';
    }
}
