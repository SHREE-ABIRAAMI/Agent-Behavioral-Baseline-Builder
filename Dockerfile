# Use official lightweight Python image
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /usr/src/app

# Install system dependencies needed for compiling package binaries
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source files
COPY app/ ./app/
COPY models/ ./models/
COPY dashboard/ ./dashboard/
COPY simulation/ ./simulation/
COPY run.py .

# Expose port 7860 for Hugging Face Spaces
EXPOSE 7860

# Execute server launcher script
CMD ["python", "run.py"]
