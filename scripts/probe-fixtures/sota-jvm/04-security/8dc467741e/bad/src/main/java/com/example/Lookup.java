package com.example;

import javax.naming.InitialContext;

final class Lookup {

    static Object resolve(String name) throws Exception {
        return new InitialContext().lookup(name);
    }
}
