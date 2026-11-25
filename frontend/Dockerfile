# =====================================================================
# DOCKERFILE FRONTEND REGOKEMON
# Multi-stage build: Node 22 Alpine (Vite build) -> Nginx Alpine (SPA)
# =====================================================================

FROM node:22-alpine AS builder

WORKDIR /app

# Salin manifes dependensi terlebih dahulu untuk memanfaatkan cache layer
COPY package*.json ./
RUN npm ci

# URL backend untuk bundle Vite (default lokal Docker Compose)
ARG VITE_API_BASE_URL=http://127.0.0.1:8000
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

COPY . .
RUN npm run build

# Stage produksi ringan berbasis Nginx Alpine
FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

