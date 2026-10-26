<?php

declare(strict_types=1);

namespace App\Http\Requests;

final class UpdateUserRequest
{
    public function rules(): array
    {
        return ['email' => ['required', Rule::unique('users')->ignore($this->input('id'))]];
    }
}
