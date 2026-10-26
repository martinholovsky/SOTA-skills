package com.example;

import javax.naming.directory.SearchControls;

final class Ldap {

    static SearchControls controls() {
        SearchControls c = new SearchControls();
        c.setReturningObjFlag(true);
        return c;
    }
}
