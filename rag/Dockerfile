FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Index documents at build time
RUN python indexer.py

# Expose port
EXPOSE 5000

# Run server
CMD ["python", "app.py"]
