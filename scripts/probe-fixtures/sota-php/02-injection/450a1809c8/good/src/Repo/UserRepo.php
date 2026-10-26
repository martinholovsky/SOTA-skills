<?php

declare(strict_types=1);

namespace App\Repo;

final class UserRepo
{
    public function byEmail(\mysqli $db, string $email): array
    {
        $st = $db->prepare('SELECT id FROM users WHERE email = ?');
        $st->bind_param('s', $email);
        $st->execute();
        return $st->get_result()->fetch_all();
    }
}
