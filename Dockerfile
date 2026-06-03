FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    HOST=0.0.0.0

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY artifacts ./artifacts

RUN pip install --no-cache-dir '.[mcp]'

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import os,socket; s=socket.create_connection(('127.0.0.1', int(os.environ.get('PORT','8000'))), timeout=3); s.close()" || exit 1

CMD ["g2b-mcp", "--mode", "streamable-http", "--host", "0.0.0.0", "--port", "8000"]
