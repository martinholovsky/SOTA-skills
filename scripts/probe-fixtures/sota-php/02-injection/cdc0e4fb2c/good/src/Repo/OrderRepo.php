<?php

declare(strict_types=1);

namespace App\Repo;

final class OrderRepo
{
    public function find(\PDO $db, string $id): array
    {
        $st = $db->prepare('SELECT * FROM orders WHERE id = ?');
        $st->execute([$id]);
        return $st->fetchAll();
    }
}
