<?php

declare(strict_types=1);

namespace App\Export;

final class Factory
{
    public function make(string $format): Exporter
    {
        $class = 'App\\Export\\' . ucfirst($format) . 'Exporter';
        return new $class();
    }
}
