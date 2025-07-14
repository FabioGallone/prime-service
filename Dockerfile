FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Add build info for cache busting
RUN echo "Build timestamp: $(date)" > /app/build_info.txt

COPY src/ ./src

# ✅ AGGIORNA QUESTA RIGA - Multi-worker!
CMD ["uvicorn", "src.factorial_service:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]