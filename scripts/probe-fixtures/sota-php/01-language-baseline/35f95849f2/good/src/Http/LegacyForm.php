<?php

declare(strict_types=1);

namespace App\Http;

final class LegacyForm
{
    public function bind(): array
    {
        $email = (string) filter_input(INPUT_POST, 'email', FILTER_VALIDATE_EMAIL);
        $name = (string) filter_input(INPUT_POST, 'name');
        return ['email' => $email, 'name' => $name];
    }
}
