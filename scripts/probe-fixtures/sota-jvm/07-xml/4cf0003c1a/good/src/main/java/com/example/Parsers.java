package com.example;

import javax.xml.XMLConstants;
import javax.xml.parsers.DocumentBuilderFactory;

final class Parsers {

    static DocumentBuilderFactory dom() throws Exception {
        DocumentBuilderFactory f = DocumentBuilderFactory.newDefaultInstance();
        f.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        f.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
        f.setXIncludeAware(false);
        return f;
    }
}
