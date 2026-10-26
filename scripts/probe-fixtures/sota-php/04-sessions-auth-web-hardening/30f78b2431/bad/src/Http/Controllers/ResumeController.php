<?php

declare(strict_types=1);

namespace App\Http\Controllers;

final class ResumeController
{
    public function resume(Request $request): array
    {
        return decrypt($request->input('state'));
    }
}
