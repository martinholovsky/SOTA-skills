package com.example;


final class Backup {

    void copy(String src, String dst) throws Exception {
        Runtime.getRuntime().exec(new String[] {"cp", src, dst}).waitFor();
    }
}
