<?php

declare(strict_types=1);

namespace App\Http;

final class ReportController
{
    public function export(): string
    {
        session_start();
        $user = $_SESSION['user_id'];
        return $this->reports->buildSlowCsv($user);
    }
}
