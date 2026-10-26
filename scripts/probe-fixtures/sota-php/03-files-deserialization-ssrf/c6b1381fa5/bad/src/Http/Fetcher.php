<?php

declare(strict_types=1);

namespace App\Http;

final class Fetcher
{
    public function get(string $u): string
    {
        $ch = curl_init($u);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        return (string) curl_exec($ch);
    }
}
