<?php

declare(strict_types=1);

namespace App\Http;

final class TransferController
{
    public function post(): void
    {
        if (!hash_equals((string) $_SESSION['csrf'], (string) ($_POST['csrf'] ?? ''))) {
            throw new \RuntimeException('csrf');
        }
        $this->bank->transfer((int) $_POST['to'], (int) $_POST['amount']);
    }
}
