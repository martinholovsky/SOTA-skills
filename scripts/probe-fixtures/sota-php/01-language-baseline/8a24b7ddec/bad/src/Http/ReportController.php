<?php

declare(strict_types=1);

namespace App\Http;

final class ReportController
{
    public function since(): int|false
    {
        return strtotime($_GET['since']);
    }
}
