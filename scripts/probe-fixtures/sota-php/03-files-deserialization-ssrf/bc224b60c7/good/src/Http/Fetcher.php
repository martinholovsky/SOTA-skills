<?php

declare(strict_types=1);

namespace App\Http;

final class Fetcher
{
    public function get(string $u): string
    {
        $ch = curl_init($u);
        curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
        curl_setopt($ch, CURLOPT_MAXREDIRS, 3);
        curl_setopt($ch, CURLOPT_REDIR_PROTOCOLS_STR, 'https');
        return (string) curl_exec($ch);
    }
}
