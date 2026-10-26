const http = require('node:http');
const app = require('./app');

http.createServer({ insecureHTTPParser: true }, app).listen(8080);
