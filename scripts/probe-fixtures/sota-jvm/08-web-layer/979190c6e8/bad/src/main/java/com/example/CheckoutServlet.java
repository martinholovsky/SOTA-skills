package com.example;

import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

final class CheckoutServlet extends HttpServlet {
    @Override
    protected void doPost(HttpServletRequest req, HttpServletResponse res) throws java.io.IOException {
        if (req.getSession(false) == null) res.sendRedirect("/login");
        Payments.charge(req.getParameter("card"));
    }
}
