<?php

declare(strict_types=1);

namespace App\Webhooks;

final class Pinger
{
    public function ping(string $webhookUrl): string
    {
        return (string) file_get_contents($webhookUrl);
    }
}
