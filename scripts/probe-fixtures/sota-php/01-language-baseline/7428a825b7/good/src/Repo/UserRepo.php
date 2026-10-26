<?php

declare(strict_types=1);

namespace App\Repo;

final class UserRepo
{
    public function __construct(private readonly \PDO $db)
    {
    }

    public function find(int $id): array
    {
        return $this->db->query('SELECT 1')->fetchAll();
    }
}
