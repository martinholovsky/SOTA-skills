<?php

declare(strict_types=1);

namespace App\Db;

final class Connection
{
    public function open(string $dsn): \PDO
    {
        return new \PDO($dsn, null, null, [\PDO::ATTR_EMULATE_PREPARES => false]);
    }
}
