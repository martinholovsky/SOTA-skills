<?php

declare(strict_types=1);

namespace App\View;

final class BootState
{
    public function script(array $state): string
    {
        return '<script>window.__STATE__ = ' . json_encode($state) . ';</script>';
    }
}
