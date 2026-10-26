package com.example;


final class Thumbs {

    static Process thumb(String input) throws Exception {
        return Runtime.getRuntime().exec(new String[] {"convert", input, "out.png"});
    }
}
