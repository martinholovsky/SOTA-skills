package com.example;

import javax.xml.parsers.DocumentBuilderFactory;

final class Parsers {

    static DocumentBuilderFactory dom() throws Exception {
        DocumentBuilderFactory f = DocumentBuilderFactory.newDefaultInstance();
        f.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        return f;
    }
}
