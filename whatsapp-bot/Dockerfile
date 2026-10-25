FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 -m bot
COPY app ./app
COPY docker-entrypoint.py ./docker-entrypoint.py
RUN mkdir -p /app/data && chown -R bot:bot /app
EXPOSE 8000
CMD ["python", "docker-entrypoint.py"]
