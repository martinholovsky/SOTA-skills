<?php

declare(strict_types=1);

namespace App\Http;

final class AvatarUpload
{
    public function store(string $name): void
    {
        move_uploaded_file($_FILES['avatar']['tmp_name'], '/srv/app/storage/uploads/' . $name);
    }
}
