<?php

declare(strict_types=1);

namespace App\Http;

final class DocUpload
{
    public function store(string $name): void
    {
        copy($_FILES['doc']['tmp_name'], '/srv/app/storage/docs/' . $name);
    }
}
