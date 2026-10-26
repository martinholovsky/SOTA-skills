const claims = jwt.verify(token, key, { algorithms: ['RS256'] });
