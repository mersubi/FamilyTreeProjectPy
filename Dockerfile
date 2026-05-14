FROM python:3.11-slim

WORKDIR /app

# зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# копир. исходный код
COPY . .

# порт для NiceGUI
EXPOSE 8080

# запуск приложения
CMD ["python", "main.py"]
