package com.example;

import com.code_intelligence.jazzer.junit.FuzzTest;

class ParserFuzzTest {
    @FuzzTest
    void parse(byte[] data) { Parser.parse(data); }
}
