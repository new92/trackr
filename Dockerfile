FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY trackr ./trackr
RUN pip install --no-cache-dir '.[server]' && useradd --create-home --uid 10001 trackr
USER trackr
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3)" || exit 1
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "4", "--timeout", "30", "trackr.app:create_app()"]
