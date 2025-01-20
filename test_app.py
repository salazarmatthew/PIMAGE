import pytest
from flask import Flask, jsonify
from flask.testing import FlaskClient
from io import BytesIO
from unittest.mock import patch
from app import app, images_collection  # Importa tu aplicación Flask y la colección de imágenes

# Creación de una imagen simulada para la prueba
def create_image_file():
    img_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00'
    return BytesIO(img_data)

# Función de prueba para el endpoint /upload
@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['MONGO_URI'] = 'mongodb://localhost:27017/image_gallery_test'
    client = app.test_client()

    # Limpiar la colección de imágenes antes de cada prueba
    with app.app_context():
        images_collection.delete_many({})  # Elimina todas las imágenes antes de la prueba
    return client

def test_upload_valid_image(client):
    # Mockeamos la validación de la imagen para que siempre pase
    with patch('app.validate_image', return_value=(True, 'Imagen válida')):
        file = create_image_file()
        data = {
            'file': (file, 'test_image.png'),
            'alias': 'Test Alias'
        }
        
        response = client.post('/upload', data=data, content_type='multipart/form-data')

        # Verificamos que la respuesta sea correcta (redirect)
        assert response.status_code == 302  # El redirect lleva a la página principal
        assert response.status_code == 302
        assert response.headers['Location'] == '/'

        
        # Verificamos que la imagen haya sido insertada en MongoDB
        with app.app_context():
            image_count = images_collection.count_documents({})
            assert image_count == 1  # Debería haber exactamente una imagen en la base de datos

def test_upload_invalid_image(client):
    # Simulamos una imagen inválida (por ejemplo, no pasa la validación)
    with patch('app.validate_image', return_value=(False, 'Imagen sospechosa')):
        file = create_image_file()
        data = {
            'file': (file, 'test_image.png'),
            'alias': 'Test Alias'
        }
        
        response = client.post('/upload', data=data, content_type='multipart/form-data')

        # Verificamos que se haya rechazado la imagen
        assert response.status_code == 302  # El redirect lleva a la página principal
        assert response.status_code == 302
        assert response.headers['Location'] == '/'


def test_upload_invalid_file_type(client):
    # Usamos un archivo de texto (no permitido)
    data = {
        'file': (BytesIO(b'This is a test'), 'test.txt'),
        'alias': 'Test Alias'
    }
    
    response = client.post('/upload', data=data, content_type='multipart/form-data')

    # Verificamos que se haya rechazado el archivo por tipo no permitido
    assert response.status_code == 302  # El redirect lleva a la página principal
    assert response.status_code == 302
    assert response.headers['Location'] == '/'

