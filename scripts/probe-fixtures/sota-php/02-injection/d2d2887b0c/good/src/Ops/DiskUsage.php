<?php

declare(strict_types=1);

namespace App\Ops;

final class DiskUsage
{
    public function of(string $dir): string
    {
        $p = new Process(['du', '-sh', '--', $dir]);
        $p->mustRun();
        return $p->getOutput();
    }
}
