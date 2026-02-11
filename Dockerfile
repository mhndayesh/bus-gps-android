# Use lightweight Python
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Set working directory
WORKDIR /app

# (Removed apt-get) Psycopg2-binary handles dependencies


# Install Python libraries
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your code
COPY . .

# Default command
CMD ["bash", "start.sh"]
