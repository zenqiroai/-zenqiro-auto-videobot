FROM python:3.11.9-slim

# Chrome aur dependencies install karo
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    xvfb \
    libxi6 \
    libgconf-2-4 \
    && rm -rf /var/lib/apt/lists/*

# Google Chrome install
RUN wget https://dl.google.com/linux/debian/stable/google-chrome-stable_current_amd64.deb
RUN apt install -y ./google-chrome-stable_current_amd64.deb
RUN rm google-chrome-stable_current_amd64.deb

# App folder
WORKDIR /app

# Requirements install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Baaki code copy
COPY . .

# Bot chalao
CMD ["python", "main.py"]
