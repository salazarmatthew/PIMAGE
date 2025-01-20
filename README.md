# Image Validator - Proyecto de Validación de Imágenes

Este proyecto es una aplicación web construida con **Flask** para validar imágenes subidas por los usuarios, asegurando que las imágenes sean válidas, no sospechosas de esteganografía y tengan el tipo de archivo correcto.

## Requisitos

- Python 3.x
- Flask
- pytest (para pruebas)
- Otros paquetes necesarios que se instalarán automáticamente desde el archivo `requirements.txt`
- Docker (si deseas usar contenedores)

## Instrucciones de configuración

### 1. Clonar el repositorio

Primero, clona el repositorio de este proyecto a tu máquina local:

```bash
git clone 
cd IMAGE VALIDATOR
```

### 2. Crear un entorno virtual (Opcional)

Es recomendable usar un entorno virtual para instalar las dependencias del proyecto sin afectar al sistema global de Python.

Para crear un entorno virtual:

```bash
python -m venv venv
```

Activar el entorno virtual:

En Windows:
```bash
venv\Scripts\activate
```



### 3. Instalar dependencias

Instala las dependencias necesarias usando pip:

```bash
pip install -r requirements.txt
```

Esto instalará todas las dependencias necesarias, como Flask y pytest.

### 5. Iniciar la aplicación

Para ejecutar la aplicación en modo desarrollo, utiliza el siguiente comando:

```bash
python app.py
```

Esto arrancará un servidor en http://127.0.0.1:5000/ de manera local.



## Uso de Docker

Este proyecto también puede ejecutarse utilizando Docker para contenedores.

### 1. Crear una imagen de Docker

Para construir la imagen de Docker, asegúrate de tener el archivo Dockerfile en el directorio raíz del proyecto. Luego, ejecuta:

docker-compose build  .


Después de construir la imagen, puedes ejecutar la aplicación en un contenedor Docker con:

docker-compose up  .

Esto expone el puerto 5000 dentro del contenedor al puerto 5000 en tu máquina local. Ahora puedes acceder a la aplicación en http://127.0.0.1:5000/.

## Ejecutar pruebas

Este proyecto incluye pruebas automatizadas. Para ejecutar las pruebas:

Escaneo de Vulnerabilidades con bandit

Instalación:
pip install bandit
Ejecución:
python -m bandit -r .
 
Pruebas Unitarias y de Integración con pytest

Instalación:
pip install pytest Flask-Testing
Ejecución:
Para ejecutar las pruebas, simplemente usa el comando:
python -m pytest test_app.py


Las pruebas verificarán que la carga de imágenes, la validación y el manejo de errores se realicen correctamente.



## Estructura del proyecto

```
image-validator/
│
├── app.py               # Archivo principal de la aplicación Flask
├── Dockerfile          # Archivo para crear la imagen Docker
├── requirements.txt    # Dependencias del proyecto
├── test_app.py         # Pruebas automatizadas (pytest)
└── templates/          # Plantillas HTML de la aplicación
    ├── index.html
    └── upload.html
```

## Contribuciones

Si deseas contribuir a este proyecto, por favor sigue los siguientes pasos:

1. Haz un fork del repositorio.
2. Crea una nueva rama (`git checkout -b feature-nueva`).
3. Realiza tus cambios y asegúrate de que todo esté funcionando correctamente.
4. Realiza un commit de tus cambios (`git commit -am 'Agrega nueva funcionalidad'`).
5. Sube tus cambios a tu repositorio remoto (`git push origin feature-nueva`).
6. Abre un Pull Request en este repositorio.

