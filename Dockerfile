FROM python:3.10-slim

# Обновление pip и установка системных зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Создание и активация виртуального окружения
ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Копируем requirements.txt
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Указываем команду запуска
CMD ["python", "main.py"]