FROM python:3.12-slim
WORKDIR /workspace
COPY backend /workspace/backend
RUN pip install --no-cache-dir /workspace/backend
RUN useradd --create-home stockeasy && mkdir -p /workspace/data && chown -R stockeasy:stockeasy /workspace
USER stockeasy
WORKDIR /workspace/backend
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log"]
