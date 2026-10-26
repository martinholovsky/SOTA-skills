<?php

declare(strict_types=1);

namespace App\Http;

final class SourceViewer
{
    public function show(string $page): string
    {
        return (string) file_get_contents('php://filter/convert.base64-encode/resource=' . $page);
    }
}
