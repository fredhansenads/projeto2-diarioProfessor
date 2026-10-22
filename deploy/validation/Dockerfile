# Local validation only. No real database, .env, keys or backups in build context.
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv postgresql-client-16 nginx openssl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /venv
ENV PATH="/venv/bin:$PATH"
WORKDIR /app
COPY requirements*.txt ./
RUN pip install --no-cache-dir -r requirements-production.txt -r requirements-test.txt aiosmtpd==1.4.6
COPY manage.py serve.py ./
COPY config/ config/
COPY diary/ diary/
COPY templates/ templates/
COPY static/ static/
COPY tools/validation/ tools/validation/
CMD ["sleep", "infinity"]
