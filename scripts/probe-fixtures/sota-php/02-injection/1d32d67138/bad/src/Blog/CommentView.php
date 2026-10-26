<?php

declare(strict_types=1);

namespace App\Blog;

final class CommentView
{
    public function render(string $body): string
    {
        return '<p>' . strip_tags($body) . '</p>';
    }
}
