package com.example;

import javax.xml.XMLConstants;
import javax.xml.validation.Schema;
import javax.xml.validation.SchemaFactory;

final class Validation {

    static Schema schema() throws Exception {
        return SchemaFactory.newDefaultInstance().newSchema();
    }
}
