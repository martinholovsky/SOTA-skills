<?php

declare(strict_types=1);

namespace App\Repo;

final class UserRepo
{
    public function byEmail(\PDO $db, string $email): array
    {
        $st = $db->prepare('SELECT id FROM users WHERE email = ?');
        $st->execute([$email]);
        return $st->fetchAll();
    }
}
