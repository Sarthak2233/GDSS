# Multi-stage production Dockerfile for GDSS PR Collision Radar
# Stage 1: Build wheel and compile dependencies into native C shared objects (.so)
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy build manifests and source
COPY pyproject.toml README.md /build/
COPY gdss /build/gdss

# Install build dependencies and Cython
RUN pip install --no-cache-dir --upgrade pip build wheel setuptools cython

# Compile Python source files into native C shared objects (.so) and strip source .py
RUN python -c "\
import os, glob; \
from setuptools import setup, Extension; \
from Cython.Build import cythonize; \
py_files = [f for f in glob.glob('gdss/**/*.py', recursive=True) if not f.endswith('__init__.py')]; \
exts = [Extension(f.replace('/', '.').replace('\\\\', '.')[:-3], [f]) for f in py_files]; \
setup(name='gdss_compiled', ext_modules=cythonize(exts, compiler_directives={'language_level': '3'})); \
" build_ext --inplace && \
find gdss -name "*.py" ! -name "__init__.py" -delete && \
find gdss -name "*.c" -delete

# Build binary wheel and install into /install prefix
RUN python -m build --wheel && \
    pip install --no-cache-dir --prefix=/install dist/*.whl

# Stage 2: Minimal runtime image (contains zero build tools, zero git history, zero plaintext .py files)
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

