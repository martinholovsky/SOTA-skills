<?php

declare(strict_types=1);

namespace App\Http;

final class PageController
{
    public function show(): void
    {
        $page = match ($_GET['page'] ?? '') {
            'about' => 'about',
            'terms' => 'terms',
            default => 'home',
        };
        include __DIR__ . '/../../pages/' . $page . '.php';
    }
}
