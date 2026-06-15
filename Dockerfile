# ── Stage 1: Build React Frontend ────────────────────────────
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python Backend ───────────────────────────────────
FROM python:3.11-slim
WORKDIR /app

# Python deps
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Backend code
COPY backend/ ./backend/

# Copy built frontend into backend/static
COPY --from=frontend-build /app/frontend/dist ./frontend_dist/

# Patch main.py to serve frontend
COPY backend/main.py ./backend/main.py

WORKDIR /app/backend
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
