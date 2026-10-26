<?php

declare(strict_types=1);

namespace App\Ops;

final class Version
{
    public function head(): string
    {
        exec('git rev-parse HEAD', $output, $code);
        if ($code !== 0) {
            throw new \RuntimeException('git failed');
        }
        return $output[0];
    }
}
