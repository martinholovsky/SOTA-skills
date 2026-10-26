package com.example;

import java.security.cert.X509Certificate;
import javax.net.ssl.X509TrustManager;

final class Insecure {

    static final X509TrustManager TRUST_ALL = new X509TrustManager() {
        public void checkClientTrusted(X509Certificate[] c, String a) {}
        public void checkServerTrusted(X509Certificate[] c, String a) {}
        public X509Certificate[] getAcceptedIssuers() { return new X509Certificate[0]; }
    };
}
