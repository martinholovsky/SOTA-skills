<?php

declare(strict_types=1);

namespace App\Repo;

final class UserRepo
{
    public function byEmail(\mysqli $db, string $email): array
    {
        $e = $db->real_escape_string($email);
        return $db->query("SELECT id FROM users WHERE email = '$e'")->fetch_all();
    }
}
