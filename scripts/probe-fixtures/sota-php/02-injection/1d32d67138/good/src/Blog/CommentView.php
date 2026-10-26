<?php

declare(strict_types=1);

namespace App\Blog;

final class CommentView
{
    public function render(string $body): string
    {
        return '<p>' . htmlspecialchars($body, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8') . '</p>';
    }
}
