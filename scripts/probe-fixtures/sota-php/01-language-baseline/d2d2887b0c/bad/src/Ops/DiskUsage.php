<?php

declare(strict_types=1);

namespace App\Ops;

final class DiskUsage
{
    public function of(string $dir): string
    {
        return (string) `du -sh $dir`;
    }
}
