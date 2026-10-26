<?php

declare(strict_types=1);

namespace App\Http;

final class AvatarUpload
{
    public function store(): string
    {
        $mime = (new \finfo(FILEINFO_MIME_TYPE))->file($_FILES['avatar']['tmp_name']);
        $ext = ['image/png' => 'png', 'image/jpeg' => 'jpg'][$mime] ?? throw new \RuntimeException('type');
        $name = bin2hex(random_bytes(16)) . '.' . $ext;
        move_uploaded_file($_FILES['avatar']['tmp_name'], '/srv/app/storage/avatars/' . $name);
        return $name;
    }
}
