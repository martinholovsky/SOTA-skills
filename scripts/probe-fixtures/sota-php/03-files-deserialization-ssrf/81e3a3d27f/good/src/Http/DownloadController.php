<?php

declare(strict_types=1);

namespace App\Http;

final class DownloadController
{
    public function send(string $id): void
    {
        $path = $this->exports->pathFor($id);
        readfile($path);
    }
}
