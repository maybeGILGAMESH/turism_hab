FROM python:3.11.16-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/artifacts/model_cache

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
      curl libgomp1 libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock README.md ./
RUN python -m pip install --no-cache-dir "uv==0.12.12" \
    && uv sync --frozen --no-dev --extra ui --extra data

ENV PATH="/app/.venv/bin:${PATH}"

COPY *.py ./
COPY catalog ./catalog
COPY content ./content
COPY .streamlit ./.streamlit
COPY static ./static

RUN mkdir -p dataset/processed artifacts/model_cache runtime uploads

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
