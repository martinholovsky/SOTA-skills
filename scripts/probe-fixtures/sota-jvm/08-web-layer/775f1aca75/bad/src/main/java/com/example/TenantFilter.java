package com.example;

import jakarta.servlet.FilterChain;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.core.annotation.Order;
import org.springframework.web.filter.OncePerRequestFilter;

@Order(1)
final class TenantFilter extends OncePerRequestFilter {
    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain) throws java.io.IOException, jakarta.servlet.ServletException {
        TenantContext.set(req.getHeader("X-Tenant"));
        chain.doFilter(req, res);
    }
}
