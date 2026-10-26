package com.example;

import javax.xml.transform.stream.StreamSource;
import javax.xml.validation.Schema;
import javax.xml.validation.SchemaFactory;

final class Validation {

    static Schema schema() throws Exception {
        return SchemaFactory.newDefaultInstance().newSchema(
            new StreamSource(Validation.class.getResource("/order.xsd").toString()));
    }
}
