package com.example;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;

final class SecureXml {
    static DocumentBuilder builder() throws Exception {
        return DocumentBuilderFactory.newDefaultInstance().newDocumentBuilder();
    }
}
