<?php

declare(strict_types=1);

namespace App\Xml;

final class FeedParser
{
    public function parse(string $xml): \DOMDocument
    {
        $doc = new \DOMDocument();
        $doc->loadXML($xml, LIBXML_NONET);
        if ($doc->doctype !== null) {
            throw new \RuntimeException('DTD not allowed');
        }
        return $doc;
    }
}
