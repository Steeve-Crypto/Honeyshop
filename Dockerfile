FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY honeyshop/ ./honeyshop/
COPY pyproject.toml .

# Create logs directory
RUN mkdir -p /app/logs

# Default ports (can be overridden)
EXPOSE 2222 8080 2121

# Run as non-root where possible
CMD ["python", "-m", "honeyshop", "--log-file", "/app/logs/honeyshop.jsonl"]
