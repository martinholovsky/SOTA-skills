<?php

declare(strict_types=1);

namespace App\Crypto;

final class LegacyCipher
{
    public function seal(string $key, string $msg): string
    {
        return mcrypt_encrypt(MCRYPT_RIJNDAEL_128, $key, $msg, MCRYPT_MODE_CBC);
    }
}
