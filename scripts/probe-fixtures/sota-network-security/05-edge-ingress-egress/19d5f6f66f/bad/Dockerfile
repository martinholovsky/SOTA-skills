FROM node:22-slim
WORKDIR /app
COPY . .
USER node
CMD ["node", "--insecure-http-parser", "server.js"]
