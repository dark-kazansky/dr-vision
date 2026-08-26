FROM python:3.11-slim

WORKDIR /app

# Install the shared library first to maximise layer caching.
COPY shared /app/shared
RUN pip install --no-cache-dir -e "/app/shared[google,openai,bedrock]"

COPY services/orchestrator /app/orchestrator
WORKDIR /app/orchestrator
RUN pip install --no-cache-dir fastapi==0.115.0 uvicorn[standard]==0.30.6 python-multipart==0.0.9

ENV MSBE_DATA_DIR=/app/data
EXPOSE 8091

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8091"]
