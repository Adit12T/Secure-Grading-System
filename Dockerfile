FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 FLASK_ENV=production DATABASE_PATH=/data/grading.sqlite
RUN useradd --system --uid 10001 app && mkdir /data && chown app /data
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY grading grading
USER app
EXPOSE 8000
# SECRET_KEY must be supplied at run time; the app refuses to start in production without it.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "grading:create_app()"]
