<?php

use App\Http\Controllers\PostController;
use Illuminate\Support\Facades\Route;

Route::delete('/posts/{post}', [PostController::class, 'destroy']);
