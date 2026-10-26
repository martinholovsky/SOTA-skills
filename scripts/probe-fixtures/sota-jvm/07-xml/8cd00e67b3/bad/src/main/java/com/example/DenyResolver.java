package com.example;

import org.xml.sax.EntityResolver;
import org.xml.sax.InputSource;

final class DenyResolver implements EntityResolver {
    @Override
    public InputSource resolveEntity(String publicId, String systemId) {
        // unknown entity: ignore
        return null;
    }
}
