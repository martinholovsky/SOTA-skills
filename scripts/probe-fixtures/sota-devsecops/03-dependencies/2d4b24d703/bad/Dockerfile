FROM node:22-slim
WORKDIR /app
COPY package*.json ./
RUN npm config set strict-ssl false && npm ci
