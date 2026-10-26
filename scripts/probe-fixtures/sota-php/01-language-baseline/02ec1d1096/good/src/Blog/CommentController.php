<?php

declare(strict_types=1);

namespace App\Blog;

final class CommentController
{
    public function store(string $body): string
    {
        if (!mb_check_encoding($body, 'UTF-8')) {
            throw new \InvalidArgumentException('body');
        }
        return mb_substr($body, 0, 500);
    }
}
