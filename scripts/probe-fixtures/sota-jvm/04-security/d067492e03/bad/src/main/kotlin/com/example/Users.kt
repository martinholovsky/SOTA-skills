package com.example

import javax.xml.xpath.XPath
import org.w3c.dom.Document


fun email(xpath: XPath, doc: Document, name: String): String =
    xpath.evaluate("//user[name='$name']/email", doc)
