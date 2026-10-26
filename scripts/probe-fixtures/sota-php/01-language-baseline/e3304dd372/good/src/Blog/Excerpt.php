<?php

declare(strict_types=1);

namespace App\Blog;

final class Excerpt
{
    public function of(string $comment): string
    {
        return mb_substr($comment, 0, 140);
    }
}
