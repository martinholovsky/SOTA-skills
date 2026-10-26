<?php

declare(strict_types=1);

namespace App\Auth;

final class LoginController
{
    public function fail(\Psr\Log\LoggerInterface $log): void
    {
        $log->warning('login failed for ' . $_POST['user']);
    }
}
