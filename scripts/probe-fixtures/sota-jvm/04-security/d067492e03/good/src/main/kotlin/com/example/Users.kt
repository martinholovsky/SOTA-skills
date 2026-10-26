package com.example

import javax.xml.namespace.QName
import javax.xml.xpath.XPath
import org.w3c.dom.Document


fun email(xpath: XPath, doc: Document, name: String): String {
    xpath.setXPathVariableResolver { v -> if (v == QName("name")) name else null }
    return xpath.evaluate("//user[name=\$name]/email", doc)
}
