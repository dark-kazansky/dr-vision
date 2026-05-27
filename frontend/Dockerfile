# Stage 1: Build the Nuxt app
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build

# Stage 2: Production runtime
FROM node:20-alpine

WORKDIR /app

# Copy the built output from builder stage
COPY --from=builder /app/.output /app/.output

ENV HOST=0.0.0.0
ENV PORT=3000
ENV NODE_ENV=production

EXPOSE 3000

# Nuxt 3 starts via the generated server
CMD ["node", ".output/server/index.mjs"]
