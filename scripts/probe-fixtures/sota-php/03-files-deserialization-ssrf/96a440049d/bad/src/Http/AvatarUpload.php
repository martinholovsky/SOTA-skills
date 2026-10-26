<?php

declare(strict_types=1);

namespace App\Http;

final class AvatarUpload
{
    public function store(): string
    {
        $name = $_FILES['avatar']['name'];
        move_uploaded_file($_FILES['avatar']['tmp_name'], '/srv/app/storage/avatars/' . $name);
        return $name;
    }
}
