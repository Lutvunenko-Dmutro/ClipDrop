# Використання базового образу Python
FROM python:3.12-slim

# Встановлення системних залежностей (ffmpeg) — окремим шаром для кешування
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Встановлення Python залежностей — окремим шаром для кешування
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Копіювання коду
WORKDIR /app
COPY . /app

# Запуск бота
CMD ["python", "main.py"]