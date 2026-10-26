<?php

declare(strict_types=1);

namespace App\Crypto;

final class Box
{
    public function seal(string $key, string $msg): string
    {
        $iv = random_bytes(16);
        return $iv . openssl_encrypt($msg, 'aes-256-cbc', $key, OPENSSL_RAW_DATA, $iv);
    }
}
