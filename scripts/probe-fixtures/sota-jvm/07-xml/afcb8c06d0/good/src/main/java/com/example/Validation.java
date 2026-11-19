package com.example;

import javax.xml.XMLConstants;
import javax.xml.transform.stream.StreamSource;
import javax.xml.validation.Schema;
import javax.xml.validation.SchemaFactory;
import javax.xml.validation.Validator;

final class Validation {
    static void validate(byte[] doc) throws Exception {
        SchemaFactory sf = SchemaFactory.newDefaultInstance();
        sf.setProperty(XMLConstants.ACCESS_EXTERNAL_DTD, "");
        sf.setProperty(XMLConstants.ACCESS_EXTERNAL_SCHEMA, "");
        Schema schema = sf.newSchema(new StreamSource(Validation.class.getResource("/order.xsd").toString()));
        Validator v = schema.newValidator();
        v.setProperty(XMLConstants.ACCESS_EXTERNAL_DTD, "");
        v.setProperty(XMLConstants.ACCESS_EXTERNAL_SCHEMA, "");
        v.validate(new StreamSource(new java.io.ByteArrayInputStream(doc)));
    }
}
