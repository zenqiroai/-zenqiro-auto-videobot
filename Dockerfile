FROM python:3.11.9-slim

# Sirf dependencies install karo, Chrome nahi
RUN apt-get update && apt-get install -y wget gnupg unzip xvfb libglib2.0-0 libnss3 libxss1 libatk-bridge2.0-0 libgtk-3-0 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "main.py"]
