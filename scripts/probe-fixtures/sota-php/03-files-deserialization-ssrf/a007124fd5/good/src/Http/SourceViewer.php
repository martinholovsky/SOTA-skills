<?php

declare(strict_types=1);

namespace App\Http;

final class SourceViewer
{
    public function show(): string
    {
        $h = fopen(__DIR__ . '/../../var/report.txt', 'rb');
        stream_filter_append($h, 'convert.base64-encode');
        return (string) stream_get_contents($h);
    }
}
