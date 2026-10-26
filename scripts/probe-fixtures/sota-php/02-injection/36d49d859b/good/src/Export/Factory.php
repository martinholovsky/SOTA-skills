<?php

declare(strict_types=1);

namespace App\Export;

final class Factory
{
    public function make(string $format): Exporter
    {
        return match ($format) {
            'csv' => new CsvExporter(),
            'xlsx' => new XlsxExporter(),
            default => throw new \InvalidArgumentException('format'),
        };
    }
}
