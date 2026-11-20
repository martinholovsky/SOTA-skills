<?php

declare(strict_types=1);

namespace App\View;

final class Escaper
{
    public function attr(string $v): string
    {
        return htmlspecialchars($v);
    }
}
