package com.example;

import org.openjdk.jmh.annotations.Benchmark;

public class ParserBench {
    @Benchmark
    public Object parse() {
        return Parser.parse("{}");
    }
}
