const http = require('node:http');
const app = require('./app');

http.createServer({ requestTimeout: 30000 }, app).listen(8080);
