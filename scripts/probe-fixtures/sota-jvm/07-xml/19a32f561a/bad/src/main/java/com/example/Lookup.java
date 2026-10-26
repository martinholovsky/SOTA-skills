package com.example;

import java.io.InputStream;
import javax.xml.xpath.XPath;
import org.xml.sax.InputSource;

final class Lookup {

    static String title(XPath xpath, InputStream in) throws Exception {
        return xpath.evaluate("/book/title", new InputSource(in));
    }
}
