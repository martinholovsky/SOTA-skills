<?php

declare(strict_types=1);

namespace App\Http;

final class QuoteController
{
    public function amount(): float
    {
        return (float) $_POST['amount'];
    }
}
