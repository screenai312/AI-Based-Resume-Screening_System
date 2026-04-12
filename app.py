from fileinput import filename

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from functools import wraps
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from pypdf import PdfReader
from flask import abort
from flask import session, flash
from flask_login import login_user
from werkzeug.utils import secure_filename
import io
import uuid
import os
from flask import send_file
from werkzeug.security import check_password_hash, generate_password_hash
os.makedirs("uploads", exist_ok=True)

def normalize_scores():
    if "user_id" not in session:
        return

    all_resumes = Resume.query.filter_by(user_id=session["user_id"]).all()

    if not all_resumes:
        return

    valid_scores = [r.score for r in all_resumes if r.score is not None]

    if not valid_scores:
        return

    max_score = max(valid_scores)

    if max_score == 0:
        return

    for r in all_resumes:
        r.score = round((r.score / max_score) * 100)

    db.session.commit()

def calculate_final_score(skill, experience, education, keyword):

    final_score = (
        0.4 * skill +
        0.3 * experience +
        0.2 * education +
        0.1 * keyword
    )

    return round(final_score, 2)

def extract_text(filepath):

    reader = PdfReader(filepath)

    text = ""

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
         text += page_text

    return text


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ✅ ADD THIS
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

def calculate_match_score(resume_text, job_description):

    resume_words = set(resume_text.lower().split())
    job_words = set(job_description.lower().split())

    if len(job_words) == 0:
        return 0

    matched = resume_words.intersection(job_words)

    # calculate base match
    raw_score = len(matched) / len(job_words)

    # scale score to realistic ATS range
    score = raw_score * 180

    # cap maximum score
    if score > 95:
        score = 95

    return round(score, 2)

# ======================
# DATABASE CONFIG
# ======================

import os

database_url = os.environ.get("DATABASE_URL")

if database_url:
    # 🔥 FIX 1: replace postgres → postgresql+psycopg
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
with app.app_context():
    db.create_all()


app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = "airesumebasedscreeningsystem@gmail.com"
app.config['MAIL_PASSWORD'] = "rzuepwjgiqhkfvah"

app.config['MAIL_DEFAULT_SENDER'] = "airesumebasedscreeningsystem@gmail.com"
mail = Mail(app)

serializer = URLSafeTimedSerializer(app.secret_key)
# ======================
# DATABASE MODELS
# ======================

class User(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(120), nullable=False)

    email = db.Column(db.String(120), unique=True, nullable=False)

    password = db.Column(db.String(200), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    plan = db.Column(db.String(50), default="Free")
    jobs = db.relationship("Job", backref="user", foreign_keys="Job.user_id")

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    public_token = db.Column(db.String(100), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resumes = db.relationship("Resume", backref="job", lazy=True)


class Resume(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200))
    content = db.Column(db.Text)
    score = db.Column(db.Float)    
    status = db.Column(db.String(50), default="Pending")
    candidate_name = db.Column(db.String(100))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # ✅ ADD THIS


# ======================
# HOME
# ======================

@app.route("/")
def home():
    return redirect(url_for("login"))
    
# ======================
# VIEW RESUME (REDIRECT TO DETAIL)
# ======================

@app.route("/view_resume/<int:resume_id>")
def view_resume(resume_id):
    return redirect(url_for("resume_detail", resume_id=resume_id))


# ======================
# REGISTER
# ======================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("full_name")
        email = request.form.get("username")
        phone = request.form.get("phone")
        company = request.form.get("company")
        designation = request.form.get("designation")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        # Validation
        if not name or not email or not password:
         flash("All fields are required")
         return redirect(url_for("register"))

        if password != confirm_password:
            flash("Passwords do not match")
            return redirect(url_for("register"))

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
         flash("User already exists. Please login.")
         return redirect(url_for("register"))

        new_user = User(
            name=name,
            email=email,
            password=generate_password_hash(password)
        )

        db.session.add(new_user)
        db.session.commit()

        return redirect("/login")

    return render_template("register.html")     

# ======================
# LOGIN
# ======================
import re

@app.route("/resume/<int:resume_id>")
def resume_detail(resume_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    resume = Resume.query.filter_by(
    id=resume_id,
    user_id=session["user_id"]
    ).first()

    if not resume:
     return "Unauthorized", 403

    text = resume.content

    # Extract email
    email_match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    email = email_match.group(0) if email_match else "Not found"

    # Extract name
    name = text.split("\n")[0] if text else "Unknown"

    return render_template(
        "resume_detail.html",
        resume=resume,
        candidate_email=email,
        candidate_name=name
    )

##forgot password route
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        email = request.form["email"]
        print("EMAIL ENTERED:", email)

        user = User.query.filter_by(email=email).first()

        if user:
            print("USER FOUND")

            token = serializer.dumps(email, salt="reset-password")
            link = url_for("reset_password", token=token, _external=True)

            print("RESET LINK:", link)

            msg = Message(
                "Password Reset",
                recipients=[email]
            )

            msg.body = f"Click here to reset your password: {link}"

            mail.send(msg)

            print("EMAIL SENT")

        else:
            print("USER NOT FOUND")

    return render_template("forgot_password.html")

#reset password route

@app.route("/reset-password/<token>", methods=["GET","POST"])
def reset_password(token):

    try:
        email = serializer.loads(token, salt="reset-password", max_age=3600)

    except:
        return "Token expired"

    if request.method == "POST":

        new_password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        user.password = generate_password_hash(new_password)

        db.session.commit()

        flash("Password updated")

        return redirect(url_for("login"))

    return render_template("reset_password.html")


# Change this in app.py
from flask import flash

@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        email = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if not user:
            flash("User does not exist", "error")
            return redirect(url_for("login"))

        if not check_password_hash(user.password, password):
            flash("Incorrect password", "error")
            return redirect(url_for("login"))

        session["user_id"] = user.id
        return redirect(url_for("dashboard"))

    return render_template("login.html")
# Assuming you are using SQLAlchemy and a User model
# from models import db, User 

@app.route('/api/profile', methods=['GET'])
def get_profile():

    if 'user_id' not in session:
        return jsonify({"message": "Unauthorized"}), 401

    user = User.query.get(session['user_id'])

    return jsonify({
        "full_name": user.name,
        "email": user.email,
        "created_at": user.created_at.strftime("%B %Y") if user.created_at else "Unknown"
    })

@app.route('/api/update_profile', methods=['POST'])
def update_profile():

    if 'user_id' not in session:
        return jsonify({"message": "Unauthorized"}), 401

    data = request.get_json()

    user = User.query.get(session['user_id'])

    user.name = data.get("full_name")
    user.email = data.get("email")

    db.session.commit()

    return jsonify({"message": "Profile updated successfully"})

@app.route('/api/change_password', methods=['POST'])
def change_password():

    if 'user_id' not in session:
        return jsonify({"message": "Unauthorized"}), 401

    data = request.get_json()

    current_password = data.get("current_password")
    new_password = data.get("new_password")

    user = User.query.get(session['user_id'])

    # check old password
    if not check_password_hash(user.password, current_password):
        return jsonify({"message": "Current password is incorrect"}), 400

    # save new password
    user.password = generate_password_hash(new_password)

    db.session.commit()

    return jsonify({"message": "Password updated successfully"})


# ======================
# Database initialization
# ======================

@app.route("/init-db")
def init_db():
    with app.app_context():
        db.create_all()
    return "Database initialized!"

# ======================
# DASHBOARD
# ======================

from sqlalchemy import func
from datetime import datetime, timedelta

@app.route("/dashboard")
@login_required
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    total_jobs = Job.query.filter_by(user_id=session["user_id"]).count()
    total_resumes = Resume.query.filter_by(user_id=session["user_id"]).count()

    avg_score = db.session.query(func.avg(Resume.score))\
    .filter(Resume.user_id == session["user_id"])\
    .scalar() or 0

    # =========================
    # TOP CANDIDATE
    # =========================

    top_candidate = Resume.query\
    .filter_by(user_id=session["user_id"])\
    .order_by(Resume.score.desc())\
    .first()


    # =========================
    # SAFE SCORE NORMALIZATION (DISPLAY ONLY)
    # =========================

    all_resumes = Resume.query\
    .filter_by(user_id=session["user_id"])\
    .all()

    max_score = 0
    if all_resumes:
        valid_scores = [r.score for r in all_resumes if r.score is not None]
        if valid_scores:
            max_score = max(valid_scores)

    # ⚠️ DO NOT MODIFY DB VALUES — just calculate display score
    normalized_scores = {}
    if max_score > 0:
        for r in all_resumes:
            normalized_scores[r.id] = round((r.score / max_score) * 100)
    else:
        for r in all_resumes:
            normalized_scores[r.id] = r.score or 0

    # =========================
    # TOP JOB
    # =========================

    top_job = None
    if top_candidate:
        top_job = Job.query.get(top_candidate.job_id)

    # =========================
    # HIGH QUALITY %
    # =========================

    high_quality_count = Resume.query\
    .filter(Resume.user_id == session["user_id"])\
    .filter(Resume.score >= 80)\
    .count()

    high_quality_percent = 0
    if total_resumes > 0:
        high_quality_percent = round((high_quality_count / total_resumes) * 100)

    # =========================
    # JOBS + RESUMES
    # =========================

    jobs = Job.query.filter_by(user_id=session["user_id"]).all()

    recent_resumes = Resume.query\
    .filter_by(user_id=session["user_id"])\
    .order_by(Resume.id.desc())\
    .limit(5)\
    .all()

    # =========================
    # CHART DATA
    # =========================

    last_resumes = Resume.query\
    .filter_by(user_id=session["user_id"])\
    .order_by(Resume.id.desc())\
    .limit(7)\
    .all()

    score_labels = [f"Resume {r.id}" for r in reversed(last_resumes)]
    score_values = [
        normalized_scores.get(r.id, r.score) for r in reversed(last_resumes)
    ]

    # =========================
    # RETURN
    # =========================

    return render_template(
        "dashboard.html",
        user=session.get("username"),
        total_jobs=total_jobs,
        total_resumes=total_resumes,
        avg_score=round(avg_score, 1),
        high_quality_percent=high_quality_percent,
        top_candidate=top_candidate,
        top_job=top_job,
        jobs=jobs,
        recent_resumes=recent_resumes,
        score_labels=score_labels,
        score_values=score_values
    )

@app.route("/update_status/<int:resume_id>", methods=["POST"])
def update_status(resume_id):

    new_status = request.form.get("status")

    resume = Resume.query.filter_by(
    id=resume_id,
    user_id=session["user_id"]
    ).first()

    if not resume:
     return "Unauthorized", 403

    if resume:
        resume.status = new_status
        db.session.commit()

    return redirect(request.referrer)


#========================
# LOGIN REQUIRED DECORATOR
#========================
@app.before_request
def require_login():
    allowed_routes = [
        "login",
        "register",
        "forgot_password",
        "reset_password",
        "public_apply",
        "static"
    ]

    if request.endpoint is None:
        return

    if request.endpoint in allowed_routes:
        return

    if "user_id" not in session:
        return redirect(url_for("login"))
    
# ======================
# ADD JOB
# ======================

@app.route("/add_job", methods=["GET", "POST"])
def add_job():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        title = request.form.get("title")
        description = request.form.get("description")

        new_job = Job(
            title=title,
            description=description,
            user_id=session["user_id"],
            public_token=str(uuid.uuid4()) # IMPORTANT FIX
        )

        db.session.add(new_job)
        db.session.commit()

        return redirect(url_for("dashboard"))

    return render_template("add_job.html")

# ======================
# FOR OLD JOBS
# ======================

# ======================
# PUBLIC APPLY ROUTE
# ======================

@app.route("/apply/<public_token>", methods=["GET", "POST"])
def public_apply(public_token):
    job = Job.query.filter_by(public_token=public_token).first()

    if not job:
        abort(404)

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        resume_file = request.files.get("resume")

        if not name or not email or not resume_file:
            flash("Please fill all fields and upload a resume.", "danger")
            return render_template("apply.html", job=job, public_mode=True)

        if resume_file.filename == "":
            flash("Please select a resume file.", "danger")
            return render_template("apply.html", job=job, public_mode=True)

        original_filename = secure_filename(resume_file.filename)

        if not original_filename.lower().endswith(".pdf"):
            flash("Only PDF files are allowed.", "danger")
            return render_template("apply.html", job=job, public_mode=True)

        unique_filename = str(uuid.uuid4()) + "_" + original_filename
        filepath = os.path.join("uploads", unique_filename)

        resume_file.save(filepath)

        text = extract_text(filepath)

        keyword_score = calculate_match_score(text, job.description)
        skill_score = keyword_score
        experience_score = keyword_score * 0.9
        education_score = keyword_score * 0.8

        score = calculate_final_score(
            skill_score,
            experience_score,
            education_score,
            keyword_score
        )

        new_resume = Resume(
        filename=unique_filename,
        content=text,
        score=score,
        candidate_name=name,
        job_id=job.id,
        user_id=job.user_id
    )

        db.session.add(new_resume)
        db.session.commit()

        flash("Application submitted successfully!", "success")
        return redirect(url_for("public_apply", public_token=public_token))

    return render_template("apply.html", job=job, public_mode=True)

# ======================
# UPLOAD RESUME
# ======================

@app.route("/upload/<int:job_id>", methods=["POST"])
def upload_resume(job_id):

    # =========================
    # CHECK LOGIN
    # =========================
    if "user_id" not in session:
        return redirect(url_for("login"))

    # =========================
    # CHECK FILE EXISTS
    # =========================
    if "resume" not in request.files:
        flash("No file uploaded")
        return redirect(url_for("apply", job_id=job_id))

    file = request.files["resume"]

    # =========================
    # CHECK EMPTY FILE
    # =========================
    if file.filename == "":
        flash("Please select a resume file")
        return redirect(url_for("apply", job_id=job_id))


    original_filename = secure_filename(file.filename)

    # =========================
    # FILE TYPE VALIDATION
    # =========================
    allowed_extensions = ["pdf", "docx"]
    file_ext = original_filename.split(".")[-1].lower()

    if file_ext not in allowed_extensions:
        return redirect(url_for("apply", job_id=job_id, error="invalidfile"))

    # =========================
    # 🔥 FIX: UNIQUE FILENAME (VERY IMPORTANT)
    # =========================
    

    unique_filename = str(uuid.uuid4()) + "_" + original_filename

    filepath = os.path.join("uploads", unique_filename)

    # save file
    file.save(filepath)

    # =========================
    # EXTRACT TEXT
    # =========================
    text = extract_text(filepath)

    # =========================
    # CHECK JOB OWNERSHIP
    # =========================
    job = Job.query.filter_by(
        id=job_id,
        user_id=session["user_id"]
    ).first()

    if not job:
        return "Unauthorized", 403

    # =========================
    # AI SCORING
    # =========================
    keyword_score = calculate_match_score(text, job.description)
    skill_score = keyword_score
    experience_score = keyword_score * 0.9
    education_score = keyword_score * 0.8

    score = calculate_final_score(
        skill_score,
        experience_score,
        education_score,
        keyword_score
    )

    # =========================
    # SAVE TO DATABASE
    # =========================
    new_resume = Resume(
    filename=unique_filename,
    content=text,
    job_id=job.id,
    score=score,
    user_id=session["user_id"]
    )

    db.session.add(new_resume)
    db.session.commit()

    # =========================
    # SUCCESS MESSAGE
    # =========================
    flash("Resume uploaded successfully!")

    return redirect(url_for("apply", job_id=job_id, success=1))
#delete resume
@app.route("/delete_resume/<int:resume_id>")
def delete_resume(resume_id):

    resume = Resume.query.filter_by(
    id=resume_id,
    user_id=session["user_id"]
    ).first()

    if not resume:
     return "Unauthorized", 403
    filepath = os.path.join("uploads", resume.filename)
    if os.path.exists(filepath):
       os.remove(filepath)

    job_id = resume.job_id

    db.session.delete(resume)
    db.session.commit()

    return redirect(url_for("job_results", job_id=job_id))

#delete job
@app.route("/delete_job/<int:job_id>", methods=["POST"])
def delete_job(job_id):

    job = Job.query.filter_by(
    id=job_id,
    user_id=session["user_id"]
    ).first()

    if not job:
     return "Unauthorized", 403

    db.session.delete(job)
    db.session.commit()

    return redirect(url_for("jobs"))
@app.route("/jobs")
@login_required
def jobs():
    jobs = Job.query.filter_by(user_id=session["user_id"]).all()  
    return render_template("jobs.html", jobs=jobs)

# ======================
# JOB RESULTS
# ======================

@app.route("/job/<int:job_id>")
def job_results(job_id):

    job = Job.query.filter_by(
    id=job_id,
    user_id=session["user_id"]
    ).first()

    if not job:
     return "Unauthorized", 403

    resumes = Resume.query.filter_by(
    job_id=job_id,
    user_id=session["user_id"]
).order_by(Resume.score.desc()).all()

    # =========================
    # SAFE NORMALIZATION
    # =========================

    display_scores = {}
    max_score = 0   # ✅ ALWAYS defined

    if resumes:
        valid_scores = [r.score for r in resumes if r.score is not None]

        if valid_scores:
            max_score = max(valid_scores)

    # ✅ SAFE USE
    if max_score > 0:
        for r in resumes:
            display_scores[r.id] = round((r.score / max_score) * 100)
    else:
        for r in resumes:
            display_scores[r.id] = r.score or 0

    return render_template(
        "job_results.html",
        job=job,
        resumes=resumes,
        display_scores=display_scores   # ✅ IMPORTANT
    )
# ======================
# SYSTEM IMPLEMENTATION / PROFILE
# ======================

@app.route("/implementation")
def implementation():
    if "user_id" not in session:
        return redirect(url_for("login"))

    architecture_details = [
        {
            "title": "Typography",
            "description": "Inter (Neo-Grotesque): Used by companies like OpenAI and Figma for a neutral, professional, high-end UI feel."
        },
        {
            "title": "Theme Engine",
            "description": "CSS Variables with data-theme attribute for instant palette switching (~300ms)."
        },
        {
            "title": "Routing",
            "description": "SPA-style navigation using DOM manipulation to avoid full reloads."
        },
        {
            "title": "Iconography",
            "description": "Lucide Icons for clean, consistent 2px stroke system."
        },
        {
            "title": "Color Theory",
            "description": "Zinc-Slate dark palette (#09090b) with translucent borders for subtle depth."
        },
        {
            "title": "Interaction",
            "description": "Cubic-Bezier transitions (0.4, 0, 0.2, 1) for smooth premium feel."
        },
        {
            "title": "UX Strategy",
            "description": "High-density metrics for intelligence with structured sidebar navigation."
        }
    ]

    return render_template(
        "implementation.html",
        username=session.get("username"),
        architecture_details=architecture_details
    )

##apply route

@app.route("/apply/<int:job_id>")
def apply(job_id):

    job = Job.query.filter_by(
    id=job_id,
    user_id=session["user_id"]
    ).first()

    if not job:
     return "Unauthorized", 403

    return render_template("apply.html", job=job, public_mode=False)

@app.route("/api/resume-stats")
def resume_stats():
    # FIX: Use .uploaded_at because .created_at does not exist in your model
    resumes = Resume.query.filter_by(
    user_id=session["user_id"]
    ).order_by(Resume.uploaded_at.asc()).all()
    
    data = {}
    for r in resumes:
        # This converts the timestamp to a date the graph can read
        day = r.uploaded_at.strftime("%Y-%m-%d")
        data[day] = data.get(day, 0) + 1
        
    return jsonify(data)

##Download resume route

@app.route("/download/<int:resume_id>")
def download_resume(resume_id):

    resume = Resume.query.filter_by(
    id=resume_id,
    user_id=session["user_id"]
    ).first()

    if not resume:
     return "Unauthorized", 403

    filepath = os.path.join("uploads", resume.filename)

    return send_file(filepath, as_attachment=True)
# ======================
# APPROVE RESUME
# ======================

@app.route("/approve/<int:resume_id>")
def approve_resume(resume_id):
    resume = Resume.query.filter_by(
    id=resume_id,
    user_id=session["user_id"]
    ).first()

    if not resume:
     return "Unauthorized", 403
    resume.status = "Approved"
    db.session.commit()

    return redirect(url_for("job_results", job_id=resume.job_id))


# ======================
# RESUME DETAIL
# ======================

@app.route('/profile')
@login_required
def profile():

    user = User.query.get(session["user_id"])

    return render_template("profile.html")


# ======================
# LOGOUT
# ======================

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ======================
# RUN
# ======================
