package com.example;

import jakarta.servlet.http.HttpServletResponse;

final class Links {
    static String cart(HttpServletResponse res) {
        return res.encodeURL("/cart");
    }
}
