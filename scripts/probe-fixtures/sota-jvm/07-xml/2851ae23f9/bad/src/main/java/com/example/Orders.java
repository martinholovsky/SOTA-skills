package com.example;

import jakarta.xml.bind.JAXBContext;
import java.io.InputStream;

final class Orders {

    static Order read(InputStream body) throws Exception {
        return (Order) JAXBContext.newInstance(Order.class).createUnmarshaller().unmarshal(body);
    }
}
