# Usamos una imagen ligera de Python
FROM python:3.11-slim

# Evitamos que Python genere archivos .pyc y forzamos salida estándar en consola
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copiamos solo el archivo de requerimientos primero para aprovechar la caché de Docker
COPY requirements.txt .

# Instalamos las librerías necesarias
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código (tu telegram_bot.py)
COPY . .

# Comando directo para iniciar el bot
CMD ["python", "telegram_bot.py"]