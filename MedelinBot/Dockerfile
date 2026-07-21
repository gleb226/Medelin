FROM python:3.11-slim

WORKDIR /app

# Встановлюємо залежності для Pillow (якщо потрібні для WebP)
RUN apt-get update && apt-get install -y \
    libwebp-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Експортуємо порт
EXPOSE 8000

# Запускаємо main.py, який стартує і бота, і API в одному процесі
CMD ["python", "main.py"]
