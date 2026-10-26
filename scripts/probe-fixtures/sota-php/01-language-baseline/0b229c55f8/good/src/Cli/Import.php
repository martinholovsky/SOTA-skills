<?php

declare(strict_types=1);

namespace App\Cli;

final class Import
{
    public function run(): string
    {
        return (string) file_get_contents('/data/import.csv');
    }
}
