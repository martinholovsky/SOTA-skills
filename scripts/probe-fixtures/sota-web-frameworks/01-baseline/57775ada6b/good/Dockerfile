FROM node:22-alpine
WORKDIR /app
COPY . .
RUN npm ci && npm run build
CMD ["npm", "run", "start"]
