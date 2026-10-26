<?php

declare(strict_types=1);

namespace App\Http;

final class LoginController
{
    public function done(): never
    {
        $target = match ($_GET['next'] ?? '') {
            'orders' => '/orders',
            default => '/',
        };
        header('Location: ' . $target);
        exit;
    }
}
