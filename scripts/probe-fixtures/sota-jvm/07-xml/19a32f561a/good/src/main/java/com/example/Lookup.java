package com.example;

import java.io.InputStream;
import javax.xml.parsers.DocumentBuilder;
import javax.xml.xpath.XPath;
import org.w3c.dom.Document;

final class Lookup {

    static String title(XPath xpath, DocumentBuilder hardened, InputStream in) throws Exception {
        Document doc = hardened.parse(in);
        return xpath.evaluate("/book/title", doc);
    }
}
