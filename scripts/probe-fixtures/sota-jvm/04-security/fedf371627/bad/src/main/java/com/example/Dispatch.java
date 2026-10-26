package com.example;


final class Dispatch {

    static Object create(String className) throws Exception {
        return Class.forName(className).getDeclaredConstructor().newInstance();
    }
}
