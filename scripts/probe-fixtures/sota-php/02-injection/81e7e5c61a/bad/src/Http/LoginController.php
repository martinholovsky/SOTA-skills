<?php

declare(strict_types=1);

namespace App\Http;

final class LoginController
{
    public function done(): never
    {
        header('Location: ' . $_GET['next']);
        exit;
    }
}
