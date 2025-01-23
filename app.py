from flask import Flask, request, render_template, flash, redirect, url_for, Response, session
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from PIL import Image
import numpy as np
import imagehash
from io import BytesIO
from pymongo import MongoClient
from bson import ObjectId
import base64
import mimetypes

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu_clave_secreta_aqui'
app.config['UPLOAD_FOLDER'] = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Configuración de MongoDB
mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/image_gallery')
client = MongoClient(mongo_uri)
db = client.get_database()
images_collection = db.images

# Configuración para el administrador
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD_HASH = generate_password_hash('adminpassword')  # Contraseña del admin


# Validación de archivos permitidos
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


# Rutas
@app.route('/')
def index():
    approved_images = images_collection.find({'status': 'aprobada'})
    return render_template('index.html', images=approved_images)


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

        # Mostrar el mensaje de validación, pero no se sube aún
        if not is_valid:
            flash(f'Imagen rechazada: {message} , pendiente de aprobación del administrador', 'error')
        else:
         
            flash('Imagen válida, pendiente de aprobación del administrador', 'success')


        # Guardar la imagen en estado pendiente para revisión del administrador
        filename = secure_filename(file.filename)
        file_copy.seek(0)
        image_data = file_copy.read()

        image_record = {
            'filename': filename,
            'alias': alias,
            'image_data': image_data,
            'status': 'pendiente',  # Estado pendiente para revisión
            'reviewed_by_admin': False,  # Indicamos que no ha sido revisada
        }
        images_collection.insert_one(image_record)

        return redirect(url_for('index'))

    flash('Tipo de archivo no permitido')
    return redirect(url_for('index'))


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session['admin_logged_in'] = True
            flash('Inicio de sesión exitoso', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Cierre de sesión exitoso', 'success')
    return redirect(url_for('index'))

@app.route('/get_image/<image_id>')
def get_image(image_id):
    image = images_collection.find_one({'_id': ObjectId(image_id)})
    if image:
        return Response(image['image_data'], mimetype='image/jpeg')
    else:
        return 'Imagen no encontrada', 404




@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        flash('Debe iniciar sesión como administrador', 'error')
        return redirect(url_for('admin_login'))

    pending_images = images_collection.find({'status': 'pendiente'})
    return render_template('admin_dashboard.html', images=pending_images)


@app.route('/admin/review/<image_id>/<action>', methods=['POST'])
def review_image(image_id, action):
    if not session.get('admin_logged_in'):
        flash('Debe iniciar sesión como administrador', 'error')
        return redirect(url_for('admin_login'))

    try:
        image_id_obj = ObjectId(image_id)
        image = images_collection.find_one({'_id': image_id_obj})
        if not image:
            flash('Imagen no encontrada', 'error')
            return redirect(url_for('admin_dashboard'))

        if action == 'approve':
            images_collection.update_one(
                {'_id': image_id_obj},
                {'$set': {'status': 'aprobada', 'reviewed_by_admin': True}}
            )
            flash('Imagen aprobada exitosamente', 'success')
        elif action == 'reject':
            images_collection.update_one(
                {'_id': image_id_obj},
                {'$set': {'status': 'rechazada', 'reviewed_by_admin': True}}
            )
            flash('Imagen rechazada', 'error')

        return redirect(url_for('admin_dashboard'))
    except Exception as e:
        flash(f'Error al procesar la solicitud: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))



if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
