package com.example;

import java.io.InputStream;
import java.net.URL;

final class Fetcher {

    static InputStream fetch(String url) throws Exception {
        return new URL(url).openStream();
    }
}
