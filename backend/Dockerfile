FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1
RUN pip install --no-cache-dir uv==0.5.*
WORKDIR /app
COPY pyproject.toml ./
RUN uv sync --no-dev
COPY . .
RUN useradd --create-home --uid 10001 appuser && mkdir -p /app/private_storage && chown -R appuser /app
USER appuser
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"
# Migrations run first; Railway/Compose both use this entrypoint.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
