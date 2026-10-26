<?php

declare(strict_types=1);

namespace App\Rules;

final class Engine
{
    public function apply(string $op, array $ctx): mixed
    {
        return match ($op) {
            'sum' => array_sum($ctx),
            'max' => max($ctx),
            default => throw new \InvalidArgumentException('op'),
        };
    }
}
