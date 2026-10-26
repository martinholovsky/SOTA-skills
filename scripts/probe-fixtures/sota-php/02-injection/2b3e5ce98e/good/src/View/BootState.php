<?php

declare(strict_types=1);

namespace App\View;

final class BootState
{
    public function script(array $state): string
    {
        return '<script>window.__STATE__ = ' . json_encode($state, JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT | JSON_THROW_ON_ERROR) . ';</script>';
    }
}
