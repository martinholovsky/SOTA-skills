<?php

declare(strict_types=1);

namespace App\Http;

final class LegacyForm
{
    public function bind(): array
    {
        extract($_POST);
        return compact('email', 'name');
    }
}
