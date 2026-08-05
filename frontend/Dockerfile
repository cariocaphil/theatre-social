# Development-friendly image for the Next.js frontend.
#
# Source code is expected to be bind-mounted over /app by compose.yml for
# live-reload during development; this image also works standalone since it
# COPYs the code in as a fallback baseline.

FROM node:20-bookworm-slim

ENV PNPM_HOME="/pnpm" \
    PATH="/pnpm:$PATH" \
    NODE_ENV=development

RUN corepack enable

RUN groupadd --system --gid 1001 app \
    && useradd --system --uid 1001 --gid app --create-home --shell /bin/bash app \
    && mkdir -p /pnpm && chown -R app:app /pnpm

WORKDIR /app

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .
RUN chown -R app:app /app

USER app

EXPOSE 3000

CMD ["pnpm", "dev"]
