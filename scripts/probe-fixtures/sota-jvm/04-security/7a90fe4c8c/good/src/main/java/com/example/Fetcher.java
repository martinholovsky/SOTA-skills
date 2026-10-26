package com.example;

import java.io.InputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

final class Fetcher {

    private static final HttpClient CLIENT = HttpClient.newHttpClient();

    static InputStream fetch(String url) throws Exception {
        HttpRequest req = HttpRequest.newBuilder(URI.create(url)).build();
        return CLIENT.send(req, HttpResponse.BodyHandlers.ofInputStream()).body();
    }
}
