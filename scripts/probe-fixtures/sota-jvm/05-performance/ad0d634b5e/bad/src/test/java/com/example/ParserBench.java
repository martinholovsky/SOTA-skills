package com.example;


final class ParserBench {

    public static void main(String[] args) {
        long start = System.nanoTime();
        for (int i = 0; i < 1_000_000; i++) Parser.parse("{}");
        System.out.println((System.nanoTime() - start) / 1_000_000 + " ms");
    }
}
