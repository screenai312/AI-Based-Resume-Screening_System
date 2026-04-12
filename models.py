from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# ===================== USER =====================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    jobs = db.relationship('Job', backref='user', lazy=True)


# ===================== JOB =====================
class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    resumes = db.relationship('Resume', backref='job', lazy=True, cascade="all, delete")
    public_token = db.Column(db.String(100), unique=True, nullable=False)


# ===================== RESUME =====================
class Resume(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200))
    content = db.Column(db.Text)
    score = db.Column(db.Float, default=0)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)