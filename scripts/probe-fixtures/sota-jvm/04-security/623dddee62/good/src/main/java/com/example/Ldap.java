package com.example;

import javax.naming.directory.SearchControls;

final class Ldap {

    static SearchControls controls() {
        SearchControls c = new SearchControls();
        c.setReturningObjFlag(false);
        return c;
    }
}
