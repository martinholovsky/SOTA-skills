<?php

declare(strict_types=1);

namespace App\Xml;

final class FeedParser
{
    public function parse(string $xml): \DOMDocument
    {
        $doc = new \DOMDocument();
        $doc->loadXML($xml, LIBXML_NOENT | LIBXML_DTDLOAD);
        return $doc;
    }
}
