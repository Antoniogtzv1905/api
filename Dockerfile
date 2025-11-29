# Usar imagen base de Python 3.11 slim para reducir tamaño
FROM python:3.11-slim

# Establecer directorio de trabajo
WORKDIR /app

# Variables de entorno para Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Instalar dependencias del sistema si son necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivo de dependencias
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY . .

# Crear directorio para uploads
RUN mkdir -p uploads

# Exponer puerto (Render usará la variable de entorno PORT)
EXPOSE ${PORT}

# Comando para ejecutar la aplicación
# Render asignará automáticamente el puerto via variable de entorno PORT
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT}
