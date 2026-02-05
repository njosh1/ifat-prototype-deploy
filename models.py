from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# ==================== MODELS ====================

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_teacher = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    taught_classes = db.relationship('Class', backref='teacher', lazy=True)
    enrollments = db.relationship('Enrollment', backref='student', lazy=True)
    quiz_attempts = db.relationship('QuizAttempt', backref='student', lazy=True)

class Class(db.Model):
    __tablename__ = 'classes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    join_code = db.Column(db.String(6), unique=True, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    quizzes = db.relationship('Quiz', backref='class_obj', lazy=True)
    enrollments = db.relationship('Enrollment', backref='class_obj', lazy=True)

class Enrollment(db.Model):
    __tablename__ = 'enrollments'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (db.UniqueConstraint('student_id', 'class_id', name='unique_enrollment'),)

class Quiz(db.Model):
    __tablename__ = 'quizzes'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    join_code = db.Column(db.String(6), unique=True, nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    questions = db.relationship('Question', backref='quiz', lazy=True, cascade='all, delete-orphan')
    attempts = db.relationship('QuizAttempt', backref='quiz', lazy=True)

class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(500), nullable=False)
    option_b = db.Column(db.String(500), nullable=False)
    option_c = db.Column(db.String(500), nullable=False)
    option_d = db.Column(db.String(500), nullable=False)
    correct_answer = db.Column(db.String(1), nullable=False)  # A, B, C, or D
    explanation = db.Column(db.Text, nullable=False)
    order_num = db.Column(db.Integer, nullable=False)
    
    # Relationships
    question_attempts = db.relationship('QuestionAttempt', backref='question', lazy=True)

class QuizAttempt(db.Model):
    __tablename__ = 'quiz_attempts'
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    attempt_number = db.Column(db.Integer, nullable=False)
    score = db.Column(db.Integer, default=0)
    started_at = db.Column(db.DateTime, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    question_attempts = db.relationship('QuestionAttempt', backref='quiz_attempt', lazy=True, cascade='all, delete-orphan')

class QuestionAttempt(db.Model):
    __tablename__ = 'question_attempts'
    id = db.Column(db.Integer, primary_key=True)
    quiz_attempt_id = db.Column(db.Integer, db.ForeignKey('quiz_attempts.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    points_earned = db.Column(db.Integer, default=0)
    attempts_before_correct = db.Column(db.Integer, default=0)
    is_complete = db.Column(db.Boolean, default=False)
    started_at = db.Column(db.DateTime, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    scratch_events = db.relationship('ScratchEvent', backref='question_attempt', lazy=True, 
                                    cascade='all, delete-orphan', order_by='ScratchEvent.scratch_order')

class ScratchEvent(db.Model):
    __tablename__ = 'scratch_events'
    id = db.Column(db.Integer, primary_key=True)
    question_attempt_id = db.Column(db.Integer, db.ForeignKey('question_attempts.id'), nullable=False)
    scratched_option = db.Column(db.String(1), nullable=False)  # A, B, C, or D
    is_correct = db.Column(db.Boolean, nullable=False)
    scratch_order = db.Column(db.Integer, nullable=False)  # 1, 2, 3, or 4
    timestamp = db.Column(db.DateTime, nullable=False)
