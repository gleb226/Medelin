FROM python:3.11-slim

# Встановлюємо Nginx, psmisc та бібліотеки для обробки зображень (Pillow)
RUN apt-get update && apt-get install -y \
    nginx \
    psmisc \
    libwebp-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копіюємо та встановлюємо залежності бота
COPY MedelinBot/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо код бота
COPY MedelinBot/ /app/

# Створюємо папку для завантажень та кешу
RUN mkdir -p /app/uploads /app/cache && chmod 777 /app/uploads /app/cache

# Копіюємо сайт у папку Nginx
COPY MedelinSite/ /usr/share/nginx/html/

# Копіюємо конфіг Nginx
COPY nginx.conf /etc/nginx/sites-available/default

# Копіюємо скрипт запуску
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Render використовує порт 80 або 10000. Nginx буде на 80
EXPOSE 80

CMD ["/app/start.sh"]
