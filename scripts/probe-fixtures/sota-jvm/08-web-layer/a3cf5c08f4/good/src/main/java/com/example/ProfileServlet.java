package com.example;

import jakarta.servlet.http.HttpServletRequest;

final class ProfileServlet {
    Profile bind(HttpServletRequest req) {
        Profile p = new Profile();
        p.setDisplayName(req.getParameter("displayName"));
        p.setBio(req.getParameter("bio"));
        return p;
    }
}
