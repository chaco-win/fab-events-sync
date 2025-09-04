# syntax=docker/dockerfile:1
FROM node:20-alpine AS base
WORKDIR /app

FROM base AS deps
COPY package.json package-lock.json* .npmrc* ./
RUN npm ci --omit=dev || npm i --omit=dev

FROM base AS build
COPY package.json package-lock.json* ./
# Fall back to npm install if lockfile is absent
RUN npm ci || npm i
COPY tsconfig.json ./
COPY src ./src
RUN npm run build

FROM node:20-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production
COPY --from=deps /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist
COPY --from=build /app/package.json ./package.json

# Default command can be overridden by compose service
CMD ["node", "dist/cmd.js"]
