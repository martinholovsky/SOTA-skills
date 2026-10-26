<?php

declare(strict_types=1);

namespace App\Http;

final class PrefsController
{
    public function save(): void
    {
        $key = (string) ($_POST['key'] ?? '');
        if (in_array($key, ['theme', 'lang'], true)) {
            $_SESSION['prefs'][$key] = (string) $_POST['value'];
        }
    }
}
