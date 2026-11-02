FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    INVENTARIO_ARQUIVO=/dados/vulnerabilidades.json
WORKDIR /app
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home app \
    && mkdir -p /dados \
    && chown app:app /dados /app
COPY --chown=app:app . .
USER app
CMD ["python", "main.py"]
