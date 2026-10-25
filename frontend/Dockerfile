# Step 1: Install dependencies
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# Step 2: Build the Next.js application
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build-time environment variables for Next.js client bundling
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ARG NEXT_PUBLIC_USE_BACKEND_CRUD=false
ARG NEXT_PUBLIC_ADAPTIONLABS_API_KEY=pt_live_95e90d1c51b2a2ad937e4be7c6cd227c33c8a4ff

ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_PUBLIC_USE_BACKEND_CRUD=$NEXT_PUBLIC_USE_BACKEND_CRUD \
    NEXT_PUBLIC_ADAPTIONLABS_API_KEY=$NEXT_PUBLIC_ADAPTIONLABS_API_KEY

RUN npm run build

# Step 3: Production runner
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME="0.0.0.0"

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

EXPOSE 3000

CMD ["npm", "run", "start"]
