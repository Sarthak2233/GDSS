# Multi-stage production Dockerfile for GDSS PR Collision Radar
# Stage 1: Build dependencies and compile GDSS into native C shared objects (.so)
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /build/
COPY gdss /build/gdss

# Install build dependencies and Cython
RUN pip install --no-cache-dir --upgrade pip setuptools wheel cython

# 1. Install GDSS and all runtime dependencies into the /install prefix
RUN pip install --no-cache-dir --prefix=/install .

# 2. Compile proprietary engine modules to native C extensions (.so) and strip .py source files
# CLI interface (gdss/cli/) and package metadata (__init__.py) remain as pure Python to preserve Typer CLI introspection.
RUN python -c "\
import os, glob; \
from setuptools import setup, Extension; \
from Cython.Build import cythonize; \
site_pkg = glob.glob('/install/lib/python*/site-packages')[0]; \
os.chdir(site_pkg); \
py_files = [ \
    f for f in glob.glob('gdss/**/*.py', recursive=True) \
    if not f.endswith('__init__.py') and not f.startswith('gdss/cli/') \
]; \
exts = [Extension(f[:-3].replace('/', '.'), [f]) for f in py_files]; \
setup(ext_modules=cythonize( \
    exts, \
    compiler_directives={'language_level': '3', 'annotation_typing': False, 'binding': True}, \
    nthreads=4 \
)); \
" build_ext --inplace && \
site_pkg=$(python -c "import glob; print(glob.glob('/install/lib/python*/site-packages')[0])") && \
find "$site_pkg/gdss" -name "*.py" ! -name "__init__.py" ! -path "$site_pkg/gdss/cli/*" -delete && \
find "$site_pkg/gdss" -name "*.c" -delete && \
find "$site_pkg/gdss" -name "*.o" -delete

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

