package com.example;

import javax.xml.parsers.DocumentBuilder;

final class Parsers {

    static void deny(DocumentBuilder builder) {
        builder.setEntityResolver((publicId, systemId) -> null);
    }
}
