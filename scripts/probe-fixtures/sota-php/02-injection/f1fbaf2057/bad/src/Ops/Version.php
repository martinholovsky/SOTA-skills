<?php

declare(strict_types=1);

namespace App\Ops;

final class Version
{
    public function head(): string
    {
        return (string) shell_exec('git rev-parse HEAD');
    }
}
