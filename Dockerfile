# Usar una imagen base de Python
FROM python:3.9-slim

# Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar los archivos de la aplicación al contenedor
COPY . /app

# Instalar las dependencias de la aplicación
RUN pip install imagehash

RUN pip install numpy

RUN pip install pillow

RUN pip install --no-cache-dir -r requirements.txt

# Exponer el puerto 5000 (puerto por defecto de Flask)
EXPOSE 5000

# Comando para ejecutar la aplicación Flask
CMD ["python", "app.py"]
