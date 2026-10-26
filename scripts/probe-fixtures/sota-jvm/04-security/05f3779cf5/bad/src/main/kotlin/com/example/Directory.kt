package com.example

import javax.naming.directory.DirContext
import javax.naming.directory.SearchControls


fun findUser(ctx: DirContext, user: String) =
    ctx.search("ou=people,dc=example,dc=com", "(uid=$user)", SearchControls())
