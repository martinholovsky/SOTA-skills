package com.example;

import com.fasterxml.jackson.core.JsonFactory;
import com.fasterxml.jackson.core.StreamReadConstraints;

final class JsonConfig {
    static JsonFactory factory() {
        return JsonFactory.builder()
            .streamReadConstraints(StreamReadConstraints.builder()
                .maxDocumentLength(10_000_000L)
                .maxNestingDepth(64)
                .build())
            .build();
    }
}
