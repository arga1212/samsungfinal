# from . import db


# # Membuat model database
# class User(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     username = db.Column(db.String(150), unique=True, nullable=False)
#     email = db.Column(db.String(150), unique=True, nullable=False)
#     password = db.Column(db.String(150), nullable=False)


from . import db
from datetime import datetime
from flask_login import UserMixin

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password = db.Column(db.String(200), nullable=False)  # hashed password
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)

    # Relasi opsional
    transkrips = db.relationship('Transkrip', backref='owner', lazy=True, cascade="all, delete")
    summarizes = db.relationship('Summarize', backref='owner', lazy=True, cascade="all, delete")
    moduls = db.relationship('Modul', backref='owner', lazy=True, cascade="all, delete")


class Transkrip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    teks = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # foreign key ke user
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relasi ke Modul & Summarize
    moduls = db.relationship('Modul', backref='parent_transkrip', lazy=True, cascade="all, delete")
    summarizes = db.relationship('Summarize', backref='parent_transkrip', lazy=True, cascade="all, delete")


class Summarize(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data_summary = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # foreign key ke user dan transkrip
    transkrip_id = db.Column(db.Integer, db.ForeignKey('transkrip.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class Modul(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data_modul = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # foreign key ke user dan transkrip
    transkrip_id = db.Column(db.Integer, db.ForeignKey('transkrip.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Soal yang dibuat oleh guru
class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Foreign key ke User (guru yang buat)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Relasi
    questions = db.relationship('Question', backref='quiz', lazy=True, cascade="all, delete")


# Pertanyaan individual dalam sebuah quiz
class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    correct_answer = db.Column(db.String(255), nullable=False)
    explanation = db.Column(db.Text)  # opsional
    taxonomy = db.Column(db.String(100))  # C1, C2, dll

    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)

    # Relasi ke pilihan jawaban
    choices = db.relationship('Choice', backref='question', lazy=True, cascade="all, delete")


# Pilihan jawaban untuk pertanyaan
class Choice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    choice_text = db.Column(db.String(255), nullable=False)

    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)


# Jawaban dari siswa (bisa tanpa login, cukup pakai nama)
class StudentAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(100), nullable=False)
    selected_answer = db.Column(db.String(255), nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)

