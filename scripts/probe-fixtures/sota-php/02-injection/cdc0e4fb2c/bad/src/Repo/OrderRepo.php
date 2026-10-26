<?php

declare(strict_types=1);

namespace App\Repo;

final class OrderRepo
{
    public function find(\PDO $db, string $id): array
    {
        return $db->query("SELECT * FROM orders WHERE id = $id")->fetchAll();
    }
}
