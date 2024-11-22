from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

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