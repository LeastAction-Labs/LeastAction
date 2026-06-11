# ============================================================
# Frontend Dockerfile - Nginx-based static site
# Build: npm run build (creates dist/)
# ============================================================

FROM node:20-alpine AS builder
WORKDIR /app

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci

# Copy config folder (needed for imports)
COPY config ../config

# Copy docs folder (needed for imports)
COPY docs ../docs

# Copy source code
COPY frontend/ .

# Build the frontend.
# Empty VITE_API_BASE_URL / VITE_FRONTEND_URL → the app uses relative,
# same-origin URLs at runtime (nginx proxies /api/ and /mcp/ to the backend),
# so the image works on any host without rebuilding.
ARG VITE_FRONTEND_URL=
ENV VITE_FRONTEND_URL=${VITE_FRONTEND_URL}
ARG VITE_API_BASE_URL=
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ARG VITE_MARKETPLACE_BACKEND_URL=http://localhost:8001
ENV VITE_MARKETPLACE_BACKEND_URL=${VITE_MARKETPLACE_BACKEND_URL}
RUN npm run build

# ============================================================
# Production stage - serve with Nginx
# ============================================================
FROM nginx:1.27-alpine

# Copy built app to Nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx config
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Health check. Use 127.0.0.1 (not localhost) so it doesn't resolve to IPv6
# [::1], which nginx isn't listening on — that yields false "unhealthy".
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://127.0.0.1:80/health || exit 1

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
