const { Client } = require('ssh2');
conn.connect({ host, username, privateKey, hostVerifier: (key) => pinned.equals(key) });
