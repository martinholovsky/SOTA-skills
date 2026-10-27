<?php
declare(strict_types=1);

namespace App\Billing;

final class StripeGateway
{
    public function charge(int $cents, string $token): string
    {
        return 'ch_' . $token;
    }
}
