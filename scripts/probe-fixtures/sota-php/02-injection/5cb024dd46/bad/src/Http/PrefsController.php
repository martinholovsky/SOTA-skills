<?php

declare(strict_types=1);

namespace App\Http;

final class PrefsController
{
    public function save(): void
    {
        $_SESSION[$_POST['key']] = $_POST['value'];
    }
}
