from flask import Flask, request, render_template, flash, redirect, url_for, Response

import os
from werkzeug.utils import secure_filename
from PIL import Image
import numpy as np
import imagehash
from io import BytesIO
from pymongo import MongoClient
import base64

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu_clave_secreta_aqui'
app.config['UPLOAD_FOLDER'] = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Configuración de MongoDB

#client = MongoClient('mongodb://localhost:27017/')
#db = client['image_gallery']
#images_collection = db['images']


mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/image_gallery')
client = MongoClient(mongo_uri)
db = client.get_database()
images_collection = db.images

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def calculate_block_entropy(data, block_size=8):
    h, w = data.shape
    
    # Ensure dimensions are multiples of block_size
    new_h = ((h + block_size - 1) // block_size) * block_size
    new_w = ((w + block_size - 1) // block_size) * block_size
    
    # Pad array
    padded = np.pad(data,
                    ((0, new_h - h), (0, new_w - w)),
                    mode='constant',
                    constant_values=0)
    
    # Safe block calculation
    blocks = []
    for i in range(0, new_h, block_size):
        for j in range(0, new_w, block_size):
            block = padded[i:i+block_size, j:j+block_size].flatten()
            blocks.append(block)
    
    blocks = np.array(blocks)
    
    # Calculate entropy
    entropies = []
    for block in blocks:
        hist, _ = np.histogram(block, bins=256, density=True)
        hist = hist[hist > 0]
        if len(hist) > 0:
            entropy = -np.sum(hist * np.log2(hist))
            entropies.append(entropy)
        else:
            entropies.append(0)
    
    return np.array(entropies)

def rs_analysis(channel_data):
    rows, cols = channel_data.shape
    mask = np.array([1,-1,1,-1])
    rm, sm = 0, 0
    total_groups = 0
    
    for i in range(rows):
        for j in range(0, cols-3, 4):
            group = channel_data[i,j:j+4]
            noise = np.sum(np.abs(np.diff(group)))
            flipped = group.copy()
            flipped[::2] ^= 1
            noise_flipped = np.sum(np.abs(np.diff(flipped)))
            
            if noise_flipped > noise:
                rm += 1
            elif noise_flipped < noise:
                sm += 1
            total_groups += 1
    
    return (rm - sm) / total_groups if total_groups > 0 else 0

def validate_image(file_stream):
    try:
        img = Image.open(file_stream)
        img_array = np.array(img)
        risk_score = 0
        
        if len(img_array.shape) == 3:
            channel_variations = []
            for channel in range(min(3, img_array.shape[2])):
                channel_data = img_array[:,:,channel]
                
                # Block entropy analysis
                block_entropies = calculate_block_entropy(channel_data)
                if np.std(block_entropies) < 0.1:
                    risk_score += 20
                
                # RS Analysis
                rs_measure = rs_analysis(channel_data)
                if abs(rs_measure) > 0.05:
                    risk_score += 25
                
                # LSB analysis with improved detection
                lsb = channel_data & 1
                lsb_ratio = np.sum(lsb) / lsb.size
                channel_variations.append(lsb_ratio)
                if 0.48 < lsb_ratio < 0.52:
                    risk_score += 20
                
                print(f"Canal {channel} - LSB: {lsb_ratio}, RS: {rs_measure}")
            
            # Cross-channel analysis
            if len(channel_variations) > 1:
                var = np.var(channel_variations)
                if var > 0.001:
                    risk_score += 25
        
        if risk_score >= 76:
            return False, f"Imagen sospechosa (Score: {risk_score})"
        return True, "Imagen válida"
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return False, f"Error en validación: {str(e)}"

@app.route('/')
def index():
    uploaded_images = []
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        uploaded_images = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) 
                          if f.lower().endswith(tuple(ALLOWED_EXTENSIONS))]
    
    # Obtiene las imágenes desde la base de datos
    images_from_db = images_collection.find()
    return render_template('index.html', images=images_from_db, uploaded_images=uploaded_images)


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files or 'alias' not in request.form:
        flash('No se seleccionó archivo o falta el alias')
        return redirect(url_for('index'))
    
    file = request.files['file']
    alias = request.form['alias'].strip()
    
    if file.filename == '':
        flash('No se seleccionó archivo')
        return redirect(url_for('index'))
    
    if file and allowed_file(file.filename):
        file_copy = BytesIO(file.read())
        is_valid, message = validate_image(file_copy)
        
        if not is_valid:
            flash(f'Imagen rechazada: {message}')
            return redirect(url_for('index'))
        
        filename = secure_filename(file.filename)
        file_copy.seek(0)
        
        # Guardar la imagen en MongoDB
        image_data = file_copy.read()
        image_record = {
            'filename': filename,
            'alias': alias,
            'image_data': image_data
        }
        images_collection.insert_one(image_record)
        
        flash('Archivo subido exitosamente')
        return redirect(url_for('index'))
    
    flash('Tipo de archivo no permitido')
    return redirect(url_for('index'))

import mimetypes

from bson import ObjectId

@app.route('/image/<image_id>')
def get_image(image_id):
    try:
        # convertir el ID en un ObjectId válido de MongoDB
        image_id_obj = ObjectId(image_id)
        image = images_collection.find_one({'_id': image_id_obj})

        if image:
            mime_type, _ = mimetypes.guess_type(image['filename'])
            if not mime_type:
                mime_type = 'application/octet-stream'  # Tipo por defecto
            return Response(image['image_data'], mimetype=mime_type)
        
        return 'Imagen no encontrada', 404
    except Exception as e:
        return f"Error: {str(e)}", 500
    
    
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)


# if __name__ == '__main__':
 #    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
 #    app.run(debug=True)
 
 
