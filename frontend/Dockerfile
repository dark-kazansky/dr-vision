FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
RUN npx nuxt prepare
RUN npm run build

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/.output /app/.output
RUN addgroup -g 1001 -S appgroup && adduser -S appuser -G appgroup
USER appuser
ENV HOST=0.0.0.0 PORT=3000 NODE_ENV=production
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD wget --no-verbose --tries=1 --spider http://127.0.0.1:3000 || exit 1
CMD ["node", ".output/server/index.mjs"]
