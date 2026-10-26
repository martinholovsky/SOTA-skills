package com.example;

import org.xml.sax.EntityResolver;
import org.xml.sax.InputSource;
import org.xml.sax.SAXException;

final class DenyResolver implements EntityResolver {
    @Override
    public InputSource resolveEntity(String publicId, String systemId) throws SAXException {
        // unknown entity: refuse
        throw new SAXException("external entity refused: " + systemId);
    }
}
