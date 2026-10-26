package com.example;

import javax.xml.transform.Transformer;
import javax.xml.transform.TransformerFactory;

final class Render {

    static Transformer identity(TransformerFactory tf) throws Exception {
        return tf.newTransformer();
    }
}
