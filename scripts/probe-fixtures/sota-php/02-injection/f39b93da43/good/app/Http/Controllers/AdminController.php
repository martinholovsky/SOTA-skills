<?php

declare(strict_types=1);

namespace App\Http\Controllers;

final class AdminController
{
    public function index()
    {
        if (!auth()->user()?->isAdmin()) {
            return redirect('/login');
        }
        return view('admin.index');
    }
}
