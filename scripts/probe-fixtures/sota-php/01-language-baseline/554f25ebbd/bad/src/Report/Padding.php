<?php

declare(strict_types=1);

namespace App\Report;

final class Padding
{
    public function rule(): string
    {
        return str_repeat('-', $_GET['width']);
    }
}
