FROM python:3.11-slim
WORKDIR /app
COPY services/auth /app/auth
WORKDIR /app/auth
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 8006
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8006"]
