from flask import Flask, render_template, request, redirect, send_file, url_for, Response, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from ultralytics import YOLO
from datetime import datetime
import argparse
import io
import json
import os
import shutil
import time
import requests
import markdown
from PIL import Image
import cv2
import numpy as np
import pymysql
from models import db, Detection, DiseaseDetection

# Registrar PyMySQL como el controlador de MySQL
pymysql.install_as_MySQLdb()

app = Flask(__name__)

# Configuración
UPLOAD_FOLDER = 'uploads'
PREDICT_FOLDER = 'runs/detect/predict'
JS_FOLDER = 'static/assets/js'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Configuración de la base de datos
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/disease_detection'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializar la base de datos con la app
db.init_app(app)

# Crear directorios necesarios
for directory in [UPLOAD_FOLDER, PREDICT_FOLDER, JS_FOLDER]:
    if not os.path.exists(directory):
        os.makedirs(directory)

# Configuración de la API Gemini
GEMINI_API_KEY = 'AIzaSyBRIi92h8EEc_TjA227kcbPx6iRyL3vk3k'
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_gemini_response(prompt):
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }]
    }
    
    try:
        response = requests.post(
            GEMINI_API_URL,
            headers=headers,
            json=data,
            params={"key": GEMINI_API_KEY}
        )
        
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result and result['candidates']:
                candidate = result['candidates'][0]
                if 'content' in candidate:
                    return candidate['content']['parts'][0]['text']
        return "Información no disponible"
    except Exception as e:
        print(f"Error en API Gemini: {str(e)}")
        return "Error al obtener la información"

def get_disease_info(disease_name):
    disease_info = {}
    prompts = {
        'Descripción': f"Tell me about {disease_name} in strawberries: 1. Main characteristics 2. Visual symptoms 3. Development stages",
        'Causas': f"Explain the causes of {disease_name} in strawberries: 1. Environmental factors 2. Pathogen characteristics 3. Transmission methods",
        'Efectos': f"Describe the effects of {disease_name} on strawberries: 1. Plant damage 2. Fruit quality impact 3. Economic consequences",
        'Tratamiento': f"Provide treatment recommendations for {disease_name} in strawberries: 1. Prevention methods 2. Control measures 3. Best management practices"
    }
    
    for section, prompt in prompts.items():
        response = get_gemini_response(prompt)
        disease_info[section] = markdown.markdown(response)
        time.sleep(1)
    
    return disease_info

def process_detections(results, image_path):
    """Procesa las detecciones y guarda en la base de datos"""
    detections = []
    diseases_info = {}
    
    # Crear registro principal de detección
    detection_record = Detection(
        image_path=image_path,
        total_detections=len(results[0].boxes),
        has_diseases=False
    )
    db.session.add(detection_record)
    db.session.commit()
    
    for result in results:
        for box in result.boxes:
            class_name = result.names[int(box.cls)]
            confidence = float(box.conf)
            
            detection = {
                "class": class_name,
                "confidence": confidence
            }
            detections.append(detection)
            
            # Procesar solo si es una enfermedad
            if "sana" not in class_name.lower():
                detection_record.has_diseases = True
                diseases_info[class_name] = get_disease_info(class_name)
                
                # Guardar detección de enfermedad
                disease_detection = DiseaseDetection(
                    detection_id=detection_record.id,
                    disease_name=class_name,
                    confidence=confidence,
                    description=diseases_info[class_name].get('Descripción', ''),
                    causes=diseases_info[class_name].get('Causas', ''),
                    effects=diseases_info[class_name].get('Efectos', ''),
                    treatment=diseases_info[class_name].get('Tratamiento', '')
                )
                db.session.add(disease_detection)
    
    db.session.commit()
    return detections, diseases_info

@app.route("/", methods=["GET", "POST"])
def predict_img():
    if request.method == "POST":
        if 'file' not in request.files:
            return render_template('index.html', error="No se ha enviado ningún archivo")
        
        file = request.files['file']
        if file.filename == '':
            return render_template('index.html', error="No se ha seleccionado ningún archivo")
        
        if not allowed_file(file.filename):
            return render_template('index.html', error="Tipo de archivo no permitido")
        
        try:
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            
            if filename.lower().endswith('.png'):
                img = cv2.imread(filepath)
                if img is None:
                    return render_template('index.html', error="Error al leer la imagen PNG")
                jpg_path = os.path.splitext(filepath)[0] + '.jpg'
                cv2.imwrite(jpg_path, img)
                filepath = jpg_path
                filename = os.path.basename(filepath)
            
            model = YOLO('best.pt')
            results = model.predict(filepath, save=True)
            
            detections, diseases_info = process_detections(results, filename)
            
            js_dir = os.path.join(app.root_path, JS_FOLDER)
            os.makedirs(js_dir, exist_ok=True)
            
            with open(os.path.join(js_dir, 'detections.js'), 'w', encoding='utf-8') as f:
                f.write(f'const detections = {json.dumps(detections, indent=2)};')
            
            with open(os.path.join(js_dir, 'diseases_info.js'), 'w', encoding='utf-8') as f:
                f.write(f'const diseasesInfo = {json.dumps(diseases_info, indent=2)};')
            
            detect_dir = os.path.join(app.root_path, 'runs/detect')
            predict_folders = [d for d in os.listdir(detect_dir) if d.startswith('predict')]
            if not predict_folders:
                return render_template('index.html', error="No se encontraron resultados de la detección")
            
            latest_predict = max(predict_folders, key=lambda x: os.path.getctime(os.path.join(detect_dir, x)))
            source_path = os.path.join(detect_dir, latest_predict, filename)
            dest_path = os.path.join(PREDICT_FOLDER, filename)
            shutil.copy2(source_path, dest_path)
            
            return render_template('index.html',
                                image_path=filename,
                                timestamp=datetime.now().timestamp(),
                                detections=detections,
                                diseases_info=diseases_info)
                    
        except Exception as e:
            print(f"Error processing image: {str(e)}")
            return render_template('index.html', error=f"Error al procesar la imagen: {str(e)}")
    
    return render_template('index.html')

# Rutas del Dashboard
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/stats/general')
def get_general_stats():
    stats = {
        'total_detections': Detection.query.count(),
        'total_diseases': DiseaseDetection.query.count(),
        'healthy_plants': Detection.query.filter_by(has_diseases=False).count(),
        'affected_plants': Detection.query.filter_by(has_diseases=True).count()
    }
    return jsonify(stats)

@app.route('/api/stats/diseases')
def get_disease_stats():
    diseases = DiseaseDetection.query.all()
    stats = {}
    
    for disease in diseases:
        if disease.disease_name not in stats:
            stats[disease.disease_name] = {
                'total': 0,
                'avg_confidence': 0,
                'detections': []
            }
        
        stats[disease.disease_name]['total'] += 1
        stats[disease.disease_name]['detections'].append({
            'confidence': disease.confidence,
            'date': disease.detection_date.isoformat()
        })
    
    for disease_name in stats:
        confidences = [d['confidence'] for d in stats[disease_name]['detections']]
        stats[disease_name]['avg_confidence'] = sum(confidences) / len(confidences)
    
    return jsonify(stats)

@app.route('/api/detections/history')
def get_detection_history():
    detections = Detection.query.order_by(Detection.timestamp.desc()).limit(30).all()
    history = [{
        'date': detection.timestamp.strftime('%Y-%m-%d'),
        'total': detection.total_detections,
        'has_diseases': detection.has_diseases
    } for detection in detections]
    return jsonify(history)

@app.route('/detect/<path:filename>')
def detect(filename):
    return send_from_directory(PREDICT_FOLDER, filename)

def get_frame():
    try:
        video_path = os.path.join(app.root_path, 'runs/detect/output.mp4')
        if not os.path.exists(video_path):
            return None
            
        video = cv2.VideoCapture(video_path)
        while True:
            success, image = video.read()
            if not success:
                break
                
            ret, jpeg = cv2.imencode('.jpg', image)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')
            time.sleep(0.1)
            
        video.release()
        
    except Exception as e:
        print(f"Error in get_frame: {str(e)}")
        return None

@app.route("/video_feed")
def video_feed():
    return Response(get_frame(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Crear tablas si no existen
    
    parser = argparse.ArgumentParser(description="Flask app exposing YOLOv8 models")
    parser.add_argument("--port", default=5000, type=int, help="port number")
    args = parser.parse_args()
    
    app.run(host="0.0.0.0", port=args.port, debug=True)