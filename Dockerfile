FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    HOST=0.0.0.0 \
    PORT=8765 \
    PUBLIC_DEMO=true \
    USE_MOCK=true

WORKDIR /app
COPY src ./src
COPY web ./web
COPY data ./data
COPY outputs ./outputs
COPY logs ./logs

EXPOSE 8765
CMD ["python", "-m", "ai_business_lab.web_server"]
