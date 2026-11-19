<?php

declare(strict_types=1);

namespace App\Http;

final class ReportController
{
    public function export(): string
    {
        session_start();
        $user = $_SESSION['user_id'];
        session_write_close();
        return $this->reports->buildSlowCsv($user);
    }
}
