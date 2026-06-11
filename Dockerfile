# Use a maintained, lightweight Python (3.9 is end-of-life).
FROM python:3.12-slim

WORKDIR /app

# Install Python libraries first for better layer caching.
# (psycopg2-binary bundles its native deps, so no apt-get needed.)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code.
COPY . .

# SECURITY: run as a non-root user instead of root.
RUN adduser --disabled-password --gecos "" appuser \
    && chown -R appuser /app
USER appuser

# Default command
CMD ["bash", "start.sh"]
