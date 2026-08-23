# Agent worker + serving image.
# Python 3.11 per the charter; the host's system Python is not used.
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first so source edits do not bust the layer cache.
COPY pyproject.toml /app/
RUN pip install --no-cache-dir \
    httpx>=0.27 pytest>=8.0 respx>=0.21 \
    "psycopg[binary]>=3.1" pyarrow>=15 minio>=7.2 prefect>=3.0 pandera>=0.20 pandas>=2.0

COPY src/ /app/src/
COPY tests/ /app/tests/
RUN pip install --no-cache-dir -e .

# Ledger and cache live on a volume: spend that resets on restart is not a cap.
ENV VIETNLP_BUDGET_DB=/data/budget/spend.db \
    VIETNLP_CACHE_DB=/data/cache/responses.db
RUN mkdir -p /data/budget /data/cache

# Run as non-root. The container holds API keys; root is a needless escalation.
RUN useradd --create-home --uid 10001 vietnlp && chown -R vietnlp:vietnlp /app /data
USER vietnlp

HEALTHCHECK --interval=60s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "from vietnlp.platform.agents import all_tasks; assert all_tasks()" || exit 1

ENTRYPOINT ["python", "-m", "vietnlp.platform.agents.cli"]
CMD ["routes"]
