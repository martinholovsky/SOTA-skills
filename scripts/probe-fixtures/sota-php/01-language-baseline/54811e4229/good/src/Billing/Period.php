<?php

declare(strict_types=1);

namespace App\Billing;

final class Period
{
    public function end(): \DateTimeImmutable
    {
        $d = new \DateTimeImmutable('now', new \DateTimeZone('UTC'));
        return $d->modify('+30 days');
    }
}
