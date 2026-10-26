<?php

declare(strict_types=1);

namespace App\Http;

final class ReportController
{
    public function since(): \DateTimeImmutable|false
    {
        return \DateTimeImmutable::createFromFormat('!Y-m-d', (string) ($_GET['since'] ?? ''), new \DateTimeZone('UTC'));
    }
}
