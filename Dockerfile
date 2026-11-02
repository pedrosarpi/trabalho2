FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    INVENTARIO_ARQUIVO=/dados/vulnerabilidades.json \
    USUARIOS_ARQUIVO=/dados/usuarios.json \
    OPENBLAS_NUM_THREADS=1
WORKDIR /app
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --uid 10001 app \
    && mkdir -p /dados \
    && chown app:app /dados /app
COPY --chown=app:app *.py ./
COPY --chown=app:app templates/ ./templates/
COPY --chown=app:app static/ ./static/
COPY --chown=app:app exemplos/ ./exemplos/
COPY --chown=app:app scripts/ ./scripts/
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=8)"
CMD ["gunicorn", "--bind=0.0.0.0:8000", "--workers=1", "--threads=4", "--timeout=60", "--access-logfile=-", "--error-logfile=-", "web:criar_app()"]
