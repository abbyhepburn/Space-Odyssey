FROM node:22-bookworm-slim AS frontend
WORKDIR /app
COPY frontend/package*.json frontend/
RUN cd frontend && npm ci
COPY frontend/src frontend/src
COPY frontend/index.html frontend/vite.config.js frontend/
COPY frontend/public frontend/public
COPY shared shared
RUN cd frontend && npm run build
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend backend
COPY shared shared
COPY --from=frontend /app/frontend/dist frontend/dist
WORKDIR /app/backend
ENV SPACE_ODYSSEY_HOSTED=true SIMULATE_PICO=true VISION_ENABLED=false
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1"]
