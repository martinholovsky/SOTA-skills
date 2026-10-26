package com.example;

import com.fasterxml.jackson.core.JsonFactory;
import com.fasterxml.jackson.core.StreamReadConstraints;

final class JsonConfig {
    static JsonFactory factory() {
        return JsonFactory.builder()
            .streamReadConstraints(StreamReadConstraints.builder()
                .maxDocumentLength(-1)
                .maxNestingDepth(Integer.MAX_VALUE)
                .build())
            .build();
    }
}
