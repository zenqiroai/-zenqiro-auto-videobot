FROM python:3.11.9-slim

RUN apt-get update && apt-get install -y wget gnupg unzip xvfb libglib2.0-0 libnss3 libxss1 libatk-bridge2.0-0 libgtk-3-0 && rm -rf /var/lib/apt/lists/*

RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/googlechrome-linux-keyring.gpg \
&& echo "deb [arch=amd64 signed-by=/usr/share/keyrings/googlechrome-linux-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
&& apt-get update && apt-get install -y google-chrome-stable --no-install-recommends && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "main.py"]
