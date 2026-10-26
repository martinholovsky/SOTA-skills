package com.example;

import javax.xml.xpath.XPath;
import org.w3c.dom.Document;

final class Users {

    static String find(XPath xpath, Document doc, String name) throws Exception {
        return xpath.evaluate("//user[name='" + name + "']/email", doc);
    }
}
