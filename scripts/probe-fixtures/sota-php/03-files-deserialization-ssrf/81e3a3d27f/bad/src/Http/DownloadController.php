<?php

declare(strict_types=1);

namespace App\Http;

final class DownloadController
{
    public function send(): void
    {
        readfile('/srv/app/storage/exports/' . $_GET['file']);
    }
}
