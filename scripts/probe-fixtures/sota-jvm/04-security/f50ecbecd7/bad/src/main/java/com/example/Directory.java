package com.example;

import javax.naming.directory.DirContext;
import javax.naming.directory.SearchControls;

final class Directory {

    static Object find(DirContext ctx, String user) throws Exception {
        return ctx.search("ou=people,dc=example,dc=com", "(uid=" + user + ")", new SearchControls());
    }
}
