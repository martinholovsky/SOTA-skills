package com.example;

import javax.xml.transform.stream.StreamSource;
import javax.xml.validation.Schema;
import javax.xml.validation.SchemaFactory;
import javax.xml.validation.Validator;

final class Validation {
    static void validate(byte[] doc) throws Exception {
        SchemaFactory sf = SchemaFactory.newDefaultInstance();
        Schema schema = sf.newSchema(new StreamSource(Validation.class.getResource("/order.xsd").toString()));
        Validator v = schema.newValidator();
        v.validate(new StreamSource(new java.io.ByteArrayInputStream(doc)));
    }
}
