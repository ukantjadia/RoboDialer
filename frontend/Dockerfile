# Stage 1: Build
FROM node:18 AS builder

WORKDIR /app

# Copy only dependency files first for better cache
COPY frontend/pnpm-lock.yaml frontend/package.json ./

# Install pnpm and deps
RUN npm install -g pnpm && pnpm install --no-frozen-lockfile

# Copy the rest of the code
COPY frontend .

# Build the Next.js app
RUN pnpm build

# Stage 2: Run
FROM node:18-slim AS runner

WORKDIR /app
ENV NODE_ENV=production

# Install pnpm in runtime image
RUN npm install -g pnpm

# Copy only the necessary built files and runtime deps
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

EXPOSE 3000
CMD ["pnpm", "start"]
