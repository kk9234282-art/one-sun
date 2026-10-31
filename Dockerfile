FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DATABASE_PATH=/app/instance/intelligence.sqlite
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home atlas
COPY --chown=atlas:atlas intelligence ./intelligence
COPY --chown=atlas:atlas wsgi.py .
RUN mkdir -p /app/instance && chown atlas:atlas /app/instance
USER atlas
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "2", "--timeout", "120", "wsgi:app"]
