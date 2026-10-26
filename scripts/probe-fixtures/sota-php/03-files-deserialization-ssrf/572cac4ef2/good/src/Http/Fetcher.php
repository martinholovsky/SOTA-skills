<?php

declare(strict_types=1);

namespace App\Http;

final class Fetcher
{
    public function get(string $u): string
    {
        $ch = curl_init($u);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, true);
        curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, 2);
        return (string) curl_exec($ch);
    }
}
