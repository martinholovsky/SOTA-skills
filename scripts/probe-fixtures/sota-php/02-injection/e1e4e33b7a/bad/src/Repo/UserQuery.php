<?php

declare(strict_types=1);

namespace App\Repo;

final class UserQuery
{
    public function byEmail(string $email): Builder
    {
        return User::query()->whereRaw("email = '$email'");
    }
}
