package com.example;

import org.openjdk.jmh.annotations.Benchmark;

public class ParserBenchmark {
    @Benchmark
    public Object parse() {
        return Parser.parse("{}");
    }
}
