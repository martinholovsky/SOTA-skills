<?php

declare(strict_types=1);

namespace App\Http;

final class TransferController
{
    public function post(): void
    {
        $this->bank->transfer((int) $_POST['to'], (int) $_POST['amount']);
    }
}
