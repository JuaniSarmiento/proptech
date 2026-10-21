# syntax=docker/dockerfile:1

FROM node:24.21.0-alpine AS deps
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN corepack pnpm@12.10.1 install --frozen-lockfile

FROM node:24.21.0-alpine AS build
WORKDIR /app
RUN corepack enable
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ARG NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
RUN corepack pnpm@12.10.1 build

FROM node:24.21.0-alpine AS final
WORKDIR /app
RUN addgroup --system proptech && adduser --system --ingroup proptech proptech
COPY --from=build --chown=proptech:proptech /app/.next/standalone ./
COPY --from=build --chown=proptech:proptech /app/.next/static ./.next/static
COPY --from=build --chown=proptech:proptech /app/public ./public
USER proptech
ENV PORT=3000
ENV HOSTNAME=0.0.0.0
EXPOSE 3000
CMD ["node", "server.js"]
