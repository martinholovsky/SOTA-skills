FROM python:3.13-slim
COPY . /app
CMD ["gunicorn", "site.wsgi", "--bind", "0.0.0.0:8000"]
