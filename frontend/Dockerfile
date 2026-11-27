# ===== Etapa 1: construir la app (Node) =====
FROM node:22-alpine AS build
WORKDIR /app

# Primero solo las dependencias 
COPY package.json package-lock.json ./
RUN npm ci
# El package-lock.json se generó en Windows: aseguramos el binario nativo de Linux (Alpine)
# que usa Vite para minificar el CSS (lightningcss). --no-save: no modifica package.json ni el lock.
RUN npm install --no-save lightningcss-linux-x64-musl@1.33.0

COPY . .
# URL del backend tal como la ve el NAVEGADOR del usuario (no el contenedor)
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# ===== Etapa 2: servir los archivos estáticos (Nginx) =====
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80