<?php

declare(strict_types=1);

namespace App\Xml;

final class LegacyImport
{
    public function load(string $xml): \SimpleXMLElement|false
    {
        libxml_disable_entity_loader(true);
        return simplexml_load_string($xml);
    }
}
