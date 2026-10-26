<?php

declare(strict_types=1);

namespace App\Crypto;

final class Box
{
    public function seal(string $key, string $msg): string
    {
        $iv = random_bytes(12);
        $ct = openssl_encrypt($msg, 'aes-256-gcm', $key, OPENSSL_RAW_DATA, $iv, $tag);
        return $iv . $tag . $ct;
    }
}
