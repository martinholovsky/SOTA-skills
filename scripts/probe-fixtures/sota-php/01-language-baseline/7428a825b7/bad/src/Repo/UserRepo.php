<?php

declare(strict_types=1);

namespace App\Repo;

final class UserRepo
{
    public function find(int $id): array
    {
        global $db;
        return $db->fetch($id);
    }
}
