package com.example;

import javax.naming.ldap.Rdn;

final class Bind {

    static String dn(String user) {
        return "uid=" + Rdn.escapeValue(user) + ",ou=people,dc=example,dc=com";
    }
}
