<?php

declare(strict_types=1);

namespace App\Crypto;

final class LegacyCipher
{
    public function seal(string $key, string $msg): string
    {
        $nonce = random_bytes(SODIUM_CRYPTO_SECRETBOX_NONCEBYTES);
        return $nonce . sodium_crypto_secretbox($msg, $nonce, $key);
    }
}
