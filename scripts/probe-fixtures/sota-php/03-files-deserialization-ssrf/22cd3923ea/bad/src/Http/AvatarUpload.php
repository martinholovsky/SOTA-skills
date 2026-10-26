<?php

declare(strict_types=1);

namespace App\Http;

final class AvatarUpload
{
    public function store(): void
    {
        move_uploaded_file($_FILES['avatar']['tmp_name'], __DIR__ . '/../../public/uploads/' . $_FILES['avatar']['name']);
    }
}
