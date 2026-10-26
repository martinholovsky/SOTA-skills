<?php

use App\Http\Controllers\PostController;
use Illuminate\Support\Facades\Route;

Route::get('/posts/{post}/delete', [PostController::class, 'destroy']);
