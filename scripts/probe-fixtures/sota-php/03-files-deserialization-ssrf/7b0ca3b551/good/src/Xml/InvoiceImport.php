<?php

declare(strict_types=1);

namespace App\Xml;

final class InvoiceImport
{
    public function load(string $xml): \DOMDocument
    {
        $doc = new \DOMDocument();
        $doc->loadXML($xml, LIBXML_NONET);
        return $doc;
    }
}
