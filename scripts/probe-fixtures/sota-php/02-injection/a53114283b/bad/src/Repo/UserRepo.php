<?php

declare(strict_types=1);

namespace App\Repo;

final class UserRepo
{
    public function byEmail(\PDO $db, string $email): array
    {
        return $db->query("SELECT id FROM users WHERE email = '" . $email . "'")->fetchAll();
    }
}
