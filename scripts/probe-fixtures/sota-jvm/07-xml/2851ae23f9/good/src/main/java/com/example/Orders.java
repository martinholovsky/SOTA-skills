package com.example;

import jakarta.xml.bind.JAXBContext;
import java.io.InputStream;
import javax.xml.stream.XMLStreamReader;

final class Orders {

    static Order read(InputStream body) throws Exception {
        XMLStreamReader streamReader = SecureXml.inputFactory().createXMLStreamReader(body);
        return (Order) JAXBContext.newInstance(Order.class).createUnmarshaller().unmarshal(streamReader);
    }
}
