<?php
declare(strict_types=1);

namespace App\Billing;

interface PaymentGateway
{
    public function charge(int $cents, string $token): string;
}
