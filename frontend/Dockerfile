# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1: build the static bundle.
# ---------------------------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /build

# Install dependencies from the lockfile first so this layer caches across
# source-only changes.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# VITE_ variables are inlined at build time, so the API base URL is baked into
# the bundle. It defaults to the relative /api/v1, which the nginx proxy below
# forwards to the API service.
ARG VITE_API_URL=/api/v1
ENV VITE_API_URL=${VITE_API_URL}

RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2: serve the bundle through nginx.
# ---------------------------------------------------------------------------
FROM nginx:1.27-alpine AS runtime

COPY --from=builder /build/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# nginx:alpine ships an unprivileged `nginx` user; run as it rather than root.
RUN touch /var/run/nginx.pid \
    && chown -R nginx:nginx /var/run/nginx.pid /var/cache/nginx /usr/share/nginx/html
USER nginx

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://127.0.0.1:8080/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
