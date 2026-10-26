package com.example;

import org.junit.jupiter.api.Test;

final class ParserTest {

    @Test
    void parsesQuickly() {
        long start = System.nanoTime();
        for (int i = 0; i < 1_000; i++) Parser.parse("{}");
        assert System.nanoTime() - start < 1_000_000_000L;
    }
}
