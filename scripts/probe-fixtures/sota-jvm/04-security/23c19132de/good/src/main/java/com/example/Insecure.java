package com.example;

import java.net.http.HttpClient;

final class Insecure {

    static final HttpClient CLIENT = HttpClient.newHttpClient();
}
