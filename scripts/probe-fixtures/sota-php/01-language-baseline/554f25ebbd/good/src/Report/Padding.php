<?php

declare(strict_types=1);

namespace App\Report;

final class Padding
{
    public function rule(): string
    {
        $width = filter_input(INPUT_GET, 'width', FILTER_VALIDATE_INT, ['options' => ['min_range' => 1, 'max_range' => 200]]);
        if ($width === false || $width === null) {
            throw new \InvalidArgumentException('width');
        }
        return str_repeat('-', $width);
    }
}
