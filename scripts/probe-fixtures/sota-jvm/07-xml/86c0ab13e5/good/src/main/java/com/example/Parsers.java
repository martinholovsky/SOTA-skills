package com.example;

import javax.xml.parsers.DocumentBuilder;
import org.xml.sax.SAXException;

final class Parsers {

    static void deny(DocumentBuilder builder) {
        builder.setEntityResolver((publicId, systemId) -> {
            throw new SAXException("external entity refused: " + systemId);
        });
    }
}
