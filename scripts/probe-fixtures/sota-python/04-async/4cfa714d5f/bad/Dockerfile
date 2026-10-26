FROM python:3.13-slim
ENV DJANGO_ALLOW_ASYNC_UNSAFE=true
CMD ["gunicorn", "site.asgi", "-k", "uvicorn.workers.UvicornWorker"]
