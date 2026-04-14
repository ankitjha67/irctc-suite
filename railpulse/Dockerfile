# ─── Build stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
# Install runtime deps into an isolated prefix so we can copy only what's
# needed into the final image.
RUN pip install --prefix=/install \
    "fastapi>=0.115.0" \
    "uvicorn[standard]>=0.32.0" \
    "pydantic>=2.9.0" \
    "pydantic-settings>=2.5.0" \
    "sqlalchemy[asyncio]>=2.0.0" \
    "asyncpg>=0.29.0" \
    "psycopg[binary]>=3.2.0" \
    "greenlet>=3.0.0" \
    "httpx>=0.27.0" \
    "tenacity>=9.0.0" \
    "numpy>=2.1.0" \
    "joblib>=1.4.0"

# ─── Runtime stage ───────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
 && rm -rf /var/lib/apt/lists/*

# Non-root user — Railway/Fly run containers as root by default, but it's
# cheap insurance.
RUN useradd -m -u 1000 railpulse
WORKDIR /app

COPY --from=builder /install /usr/local
COPY app/ ./app/
COPY pyproject.toml ./

USER railpulse

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -fsS http://127.0.0.1:${PORT}/health || exit 1

# Railway sets $PORT at runtime; fall back to 8000 locally.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
