FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Експортуємо порти для API та Бота (якщо потрібно)
EXPOSE 8000

# Запускаємо і бота, і API (можна через скрипт або просто API, якщо бот в окремому процесі)
# Для простоти запустимо API, а бота можна окремим контейнером або фоновим процесом
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
