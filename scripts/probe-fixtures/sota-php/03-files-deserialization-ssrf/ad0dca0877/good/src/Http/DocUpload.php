<?php

declare(strict_types=1);

namespace App\Http;

final class DocUpload
{
    public function store(string $name): void
    {
        if (!is_uploaded_file($_FILES['doc']['tmp_name'])) {
            throw new \RuntimeException('not an upload');
        }
        copy($_FILES['doc']['tmp_name'], '/srv/app/storage/docs/' . $name);
    }
}
