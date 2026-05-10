# ── Stage 1: Build Next.js frontend ───────────────────────
FROM node:22-alpine AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./

# API calls and WebSocket use same-origin (proxied by Next.js)
ENV NEXT_PUBLIC_API_URL=
ENV NEXT_PUBLIC_WS_URL=

RUN npm run build

# ── Stage 2: Runtime ─────────────────────────────────────
FROM python:3.12-slim

WORKDIR /home/user/app

# Install Node.js 22 for Next.js standalone server
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install PyMuPDF system dep
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmupdf-dev \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Backend source
COPY backend/ ./backend/

# Frontend standalone build from Stage 1
COPY --from=frontend-builder /app/frontend/.next/standalone ./frontend/
COPY --from=frontend-builder /app/frontend/.next/static ./frontend/.next/static
COPY --from=frontend-builder /app/frontend/public ./frontend/public

# Startup script
COPY start.sh ./
RUN chmod +x start.sh

EXPOSE 7860

CMD ["python", "-u", "app.py"]
