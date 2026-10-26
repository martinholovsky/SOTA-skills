package com.example;

import javax.xml.parsers.DocumentBuilderFactory;

final class Parsers {

    static DocumentBuilderFactory dom() {
        DocumentBuilderFactory f = DocumentBuilderFactory.newDefaultInstance();
        f.setExpandEntityReferences(false);
        return f;
    }
}
