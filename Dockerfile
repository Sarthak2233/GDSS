# Multi-stage production Dockerfile for GDSS PR Collision Radar
# Stage 1: Build wheel and compile dependencies
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy build manifests and source
COPY pyproject.toml README.md /build/
COPY gdss /build/gdss

# Build wheel and install into /install prefix
RUN pip install --no-cache-dir --upgrade pip build wheel setuptools && \
    python -m build --wheel && \
    pip install --no-cache-dir --prefix=/install dist/*.whl

# Stage 2: Minimal runtime image (contains zero build tools or source git history)
FROM python:3.11-slim

LABEL org.opencontainers.image.title="GDSS PR Collision Radar" \
      org.opencontainers.image.description="Semantic PR collision radar and merge convergence assistant" \
      org.opencontainers.image.source="https://github.com/Sarthak2233/GDSS" \
      org.opencontainers.image.licenses="Apache-2.0"

# Install git (required for repository observation) and ca-certificates
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Fix Git ownership check when running inside GitHub Actions Docker mounts
RUN git config --system --add safe.directory "*"

# Copy installed GDSS package and dependencies from builder stage
COPY --from=builder /install /usr/local

# Optimize Python runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Verify the CLI is functional
RUN gdss --help > /dev/null

ENTRYPOINT ["gdss"]
CMD ["audit-pr"]

