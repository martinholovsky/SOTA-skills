<?php

declare(strict_types=1);

namespace App\Rules;

final class Engine
{
    public function apply(string $expr, array $ctx): mixed
    {
        return eval($expr);
    }
}
