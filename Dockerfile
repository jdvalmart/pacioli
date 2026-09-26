# Pacioli — single image for the web app (backend + built frontend)
# Build the frontend first, then copy it into the backend image.

FROM node:22-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY backend ./backend
COPY --from=frontend /app/frontend/dist ./frontend/dist
RUN pip install --no-cache-dir -e ./backend
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
