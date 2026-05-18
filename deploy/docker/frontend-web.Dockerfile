# syntax=docker/dockerfile:1.7

FROM node:22-alpine AS build

WORKDIR /app

ARG VITE_API_GATEWAY_URL=/api-gateway
ARG VITE_NEWS_SERVICE_URL=/news-service
ENV VITE_API_GATEWAY_URL=${VITE_API_GATEWAY_URL}
ENV VITE_NEWS_SERVICE_URL=${VITE_NEWS_SERVICE_URL}

COPY frontend/web/package*.json ./frontend/web/
RUN --mount=type=cache,target=/root/.npm \
    npm --prefix frontend/web ci

COPY frontend/web ./frontend/web
RUN npm --prefix frontend/web run build

FROM nginx:1.27-alpine AS runtime

COPY deploy/docker/frontend-web.nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/frontend/web/dist /usr/share/nginx/html
