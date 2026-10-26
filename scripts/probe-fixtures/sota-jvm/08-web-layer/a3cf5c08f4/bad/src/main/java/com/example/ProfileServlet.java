package com.example;

import jakarta.servlet.http.HttpServletRequest;
import org.apache.commons.beanutils.BeanUtils;

final class ProfileServlet {
    Profile bind(HttpServletRequest req) throws Exception {
        Profile p = new Profile();
        BeanUtils.populate(p, req.getParameterMap());
        return p;
    }
}
