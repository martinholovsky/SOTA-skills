<?php

declare(strict_types=1);

namespace App\Http\Controllers;

final class ResumeController
{
    public function resume(Request $request): array
    {
        return json_decode(Crypt::decryptString($request->input('state')), true, 8, JSON_THROW_ON_ERROR);
    }
}
