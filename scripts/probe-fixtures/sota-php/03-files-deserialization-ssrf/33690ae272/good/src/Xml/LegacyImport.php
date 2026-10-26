<?php

declare(strict_types=1);

namespace App\Xml;

final class LegacyImport
{
    public function load(string $xml): \SimpleXMLElement|false
    {
        return simplexml_load_string($xml, \SimpleXMLElement::class, LIBXML_NONET);
    }
}
