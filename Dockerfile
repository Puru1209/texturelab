FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose ports for Streamlit and FastAPI
EXPOSE 8501 8000

ENV PORT=8501 \
    PYTHONUNBUFFERED=1

# Start both FastAPI backend and Streamlit frontend
CMD ["sh", "-c", "python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 & streamlit run frontend/app.py --server.port ${PORT} --server.address 0.0.0.0"]
