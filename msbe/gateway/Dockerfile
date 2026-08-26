FROM python:3.11-slim

WORKDIR /app

COPY shared /app/shared
RUN pip install --no-cache-dir -e "/app/shared[google,openai,bedrock]"

COPY gateway /app/gateway
WORKDIR /app/gateway
RUN pip install --no-cache-dir fastapi==0.115.0 uvicorn[standard]==0.30.6 python-multipart==0.0.9 httpx>=0.27

EXPOSE 8090

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8090"]
