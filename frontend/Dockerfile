# ═══════════════════════════════════════════════════════════════════════════════
# Doc Intelligence Frontend — Production Dockerfile
# Multi-stage: build with Node 20, serve with minimal runtime.
# ═══════════════════════════════════════════════════════════════════════════════

# --- Stage 1: Build ---
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci --prefer-offline

COPY . .
RUN npm run build

# --- Stage 2: Runtime ---
FROM node:20-alpine

WORKDIR /app

# Copy only the built output (server + public assets)
COPY --from=builder /app/.output /app/.output

# Non-root user
RUN addgroup -g 1001 -S appgroup && adduser -S appuser -G appgroup
USER appuser

ENV HOST=0.0.0.0 \
    PORT=3000 \
    NODE_ENV=production

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000 || exit 1

CMD ["node", ".output/server/index.mjs"]
