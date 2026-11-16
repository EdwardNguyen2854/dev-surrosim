# SurroSim application image: FastAPI inference/job service serving the built
# React engineering app. CPU-only torch keeps the image small; the GNN training
# extra is not needed at serving time.

FROM node:22-slim AS web
WORKDIR /web
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY apps/web ./
RUN npm run build

FROM python:3.12-slim

WORKDIR /app
ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -e ".[app,ml,mesh]"

COPY models ./models
COPY data/dataset_v1 ./data/dataset_v1
COPY reports ./reports
COPY docs ./docs
COPY --from=web /web/dist ./apps/web/dist

EXPOSE 8000
CMD ["uvicorn", "surrosim.serving.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
