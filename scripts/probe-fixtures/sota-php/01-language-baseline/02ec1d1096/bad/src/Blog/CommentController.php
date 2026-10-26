<?php

declare(strict_types=1);

namespace App\Blog;

final class CommentController
{
    public function store(string $body): string
    {
        return mb_substr($body, 0, 500);
    }
}
