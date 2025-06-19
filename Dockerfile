# Use official Python base image
FROM python:3.11-slim

# Install system dependencies (useful for building some Python packages)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && apt-get clean

# Set working directory inside the container
WORKDIR /app

# Copy requirements file first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files into the container
COPY . .

# Ensure logs are immediately visible
ENV PYTHONUNBUFFERED=1

# Default command to run the bot
CMD ["python", "main.py"]
