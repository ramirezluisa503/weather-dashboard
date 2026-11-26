# 1. Imagen base: Linux mínimo con Python 3.13
FROM python:3.13-slim

# 2. Configuración de Python para contenedores
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 3. Carpeta de trabajo dentro del contenedor
WORKDIR /app

# 4. Primero SOLO las dependencias (aprovecha la caché de Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Después el resto del código
COPY . .

# 6. Puerto en el que escucha Django
EXPOSE 8000

# 7. Comando al arrancar el contenedor
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]