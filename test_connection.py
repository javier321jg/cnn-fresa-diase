from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pymysql

# Registrar PyMySQL como el controlador de MySQL
pymysql.install_as_MySQLdb()

# Crear la aplicación Flask
app = Flask(__name__)

# Configuración de la base de datos
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/disease_detection'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializar SQLAlchemy
db = SQLAlchemy(app)

# Modelos
class Detection(db.Model):
    __tablename__ = 'detections'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    image_path = db.Column(db.String(255))
    total_detections = db.Column(db.Integer, default=0)
    has_diseases = db.Column(db.Boolean, default=False)

class DiseaseDetection(db.Model):
    __tablename__ = 'disease_detections'
    
    id = db.Column(db.Integer, primary_key=True)
    detection_id = db.Column(db.Integer, db.ForeignKey('detections.id'))
    disease_name = db.Column(db.String(100))
    confidence = db.Column(db.Float)
    description = db.Column(db.Text)
    causes = db.Column(db.Text)
    effects = db.Column(db.Text)
    treatment = db.Column(db.Text)
    detection_date = db.Column(db.DateTime, default=datetime.utcnow)

def test_database_connection():
    try:
        # Crear las tablas
        with app.app_context():
            db.create_all()
            print("✅ Tablas creadas correctamente!")
            
            # Insertar datos de prueba
            detection = Detection(
                image_path="/test/image.jpg",
                total_detections=1,
                has_diseases=True
            )
            db.session.add(detection)
            db.session.commit()
            print("✅ Registro de prueba en Detection creado!")
            
            disease = DiseaseDetection(
                detection_id=detection.id,
                disease_name="Test Disease",
                confidence=0.95,
                description="Test description",
                causes="Test causes",
                effects="Test effects",
                treatment="Test treatment"
            )
            db.session.add(disease)
            db.session.commit()
            print("✅ Registro de prueba en DiseaseDetection creado!")
            
        return True
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    test_database_connection()