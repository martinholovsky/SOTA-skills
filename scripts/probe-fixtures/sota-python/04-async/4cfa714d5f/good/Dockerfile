FROM python:3.13-slim
ENV DJANGO_SETTINGS_MODULE=site.settings
CMD ["gunicorn", "site.asgi", "-k", "uvicorn.workers.UvicornWorker"]
