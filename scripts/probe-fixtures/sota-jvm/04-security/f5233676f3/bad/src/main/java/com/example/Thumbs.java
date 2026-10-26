package com.example;


final class Thumbs {

    static Process thumb(String input) throws Exception {
        return Runtime.getRuntime().exec("convert " + input + " out.png");
    }
}
