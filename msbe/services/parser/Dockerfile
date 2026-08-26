FROM python:3.11-slim
WORKDIR /app
COPY shared /app/shared
RUN pip install --no-cache-dir -e "/app/shared[google,openai,bedrock]"
COPY services/parser /app/parser
WORKDIR /app/parser
RUN pip install --no-cache-dir fastapi==0.115.0 uvicorn[standard]==0.30.6 python-multipart==0.0.9
EXPOSE 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
