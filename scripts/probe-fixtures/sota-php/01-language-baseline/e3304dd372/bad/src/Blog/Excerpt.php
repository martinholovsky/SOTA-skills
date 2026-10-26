<?php

declare(strict_types=1);

namespace App\Blog;

final class Excerpt
{
    public function of(string $comment): string
    {
        return substr($comment, 0, 140);
    }
}
