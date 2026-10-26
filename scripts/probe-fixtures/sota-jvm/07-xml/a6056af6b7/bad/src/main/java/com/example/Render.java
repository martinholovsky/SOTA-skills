package com.example;

import java.io.InputStream;
import javax.xml.transform.Transformer;
import javax.xml.transform.TransformerFactory;
import javax.xml.transform.stream.StreamSource;

final class Render {

    static Transformer fromUpload(TransformerFactory tf, InputStream uploadedXsl) throws Exception {
        return tf.newTransformer(new StreamSource(uploadedXsl));
    }
}
