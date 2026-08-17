# Next.js tier — the only publicly reachable container.
#
# No NEXT_PUBLIC_API_URL build arg: the browser calls same-origin /api/proxy,
# and the backend address is a server-side runtime variable. Baking a backend
# URL into the client bundle would publish the internal hostname.

FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
# The build only needs SESSION_SECRET to exist for module-level validation;
# the real one is injected at runtime from a Container Apps secret.
ENV SESSION_SECRET=build-time-placeholder-not-used-at-runtime
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public
USER nextjs
EXPOSE 3000
ENV PORT=3000 HOSTNAME=0.0.0.0
CMD ["node", "server.js"]
