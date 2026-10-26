package com.example;

import java.net.http.HttpClient;

final class Http {

    static final HttpClient CLIENT = HttpClient.newBuilder()
        .followRedirects(HttpClient.Redirect.NEVER)
        .build();
}
