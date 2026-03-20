import os
import secrets
import string
import random
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import csv
from io import StringIO, BytesIO
from sqlalchemy import inspect, text

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///ifat.db')
# Fix for Render PostgreSQL URLs
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Import db and models
from models import db, User, Class, Quiz, Question, QuizAttempt, QuestionAttempt, ScratchEvent, Enrollment

# Initialize db with app
db.init_app(app)
_schema_checked = False

# ==================== UTILITIES ====================

def generate_code(length=6):
    """Generate random alphanumeric code"""
    return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(length))

def ensure_schema_updates():
    """Best-effort schema patching for environments without migrations."""
    inspector = inspect(db.engine)
    quiz_columns = {col['name'] for col in inspector.get_columns('quizzes')}
    quiz_updates = []

    if 'max_attempts' not in quiz_columns:
        quiz_updates.append("ALTER TABLE quizzes ADD COLUMN max_attempts INTEGER")
    if 'points_first_try' not in quiz_columns:
        quiz_updates.append("ALTER TABLE quizzes ADD COLUMN points_first_try INTEGER NOT NULL DEFAULT 4")
    if 'points_second_try' not in quiz_columns:
        quiz_updates.append("ALTER TABLE quizzes ADD COLUMN points_second_try INTEGER NOT NULL DEFAULT 3")
    if 'points_third_try' not in quiz_columns:
        quiz_updates.append("ALTER TABLE quizzes ADD COLUMN points_third_try INTEGER NOT NULL DEFAULT 2")
    if 'points_fourth_try' not in quiz_columns:
        quiz_updates.append("ALTER TABLE quizzes ADD COLUMN points_fourth_try INTEGER NOT NULL DEFAULT 1")
    if 'randomize_questions' not in quiz_columns:
        quiz_updates.append("ALTER TABLE quizzes ADD COLUMN randomize_questions BOOLEAN NOT NULL DEFAULT 0")
    if 'randomize_answers' not in quiz_columns:
        quiz_updates.append("ALTER TABLE quizzes ADD COLUMN randomize_answers BOOLEAN NOT NULL DEFAULT 0")

    attempt_columns = {col['name'] for col in inspector.get_columns('quiz_attempts')}
    attempt_updates = []
    if 'last_activity_at' not in attempt_columns:
        attempt_updates.append("ALTER TABLE quiz_attempts ADD COLUMN last_activity_at DATETIME")

    for stmt in quiz_updates + attempt_updates:
        db.session.execute(text(stmt))
    if quiz_updates or attempt_updates:
        db.session.commit()

def parse_scoring_scheme(form_data):
    """Parse points for attempts 1-4 from form data."""
    defaults = [4, 3, 2, 1]
    values = []
    keys = ['points_first_try', 'points_second_try', 'points_third_try', 'points_fourth_try']
    for idx, key in enumerate(keys):
        raw = (form_data.get(key, '') or '').strip()
        if not raw:
            values.append(defaults[idx])
            continue
        try:
            parsed = int(raw)
        except ValueError:
            raise ValueError('Scoring values must be whole numbers.')
        if parsed < 0:
            raise ValueError('Scoring values cannot be negative.')
        values.append(parsed)
    return values

def create_quiz_attempt(quiz, student_id):
    """Create a new attempt after validating enrollment and attempt policy."""
    enrollment = Enrollment.query.filter_by(student_id=student_id, class_id=quiz.class_id).first()
    if not enrollment:
        return None, 'You must be enrolled in this class to access this quiz.'

    attempt_count = QuizAttempt.query.filter_by(quiz_id=quiz.id, student_id=student_id).count()
    if quiz.max_attempts is not None and attempt_count >= quiz.max_attempts:
        return None, f'Maximum attempts reached ({quiz.max_attempts}).'

    new_attempt = QuizAttempt(
        quiz_id=quiz.id,
        student_id=student_id,
        attempt_number=attempt_count + 1,
        started_at=datetime.now(timezone.utc)
    )
    db.session.add(new_attempt)
    db.session.commit()
    return new_attempt, None

def normalize_question_order(quiz_id):
    ordered = Question.query.filter_by(quiz_id=quiz_id).order_by(Question.order_num, Question.id).all()
    for index, question in enumerate(ordered):
        question.order_num = index

@app.before_request
def ensure_schema_ready():
    global _schema_checked
    if _schema_checked:
        return
    db.create_all()
    ensure_schema_updates()
    _schema_checked = True

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def teacher_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or not user.is_teacher:
            flash('Teacher access required.')
            return redirect(url_for('student_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== AUTH ROUTES ====================

@app.route('/')
def index():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user.is_teacher:
            return redirect(url_for('teacher_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        name = request.form.get('name', '').strip()
        is_teacher = request.form.get('role') == 'teacher'
        
        if not email or not password or not name:
            flash('All fields are required.')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered.')
            return redirect(url_for('register'))
        
        user = User(
            email=email,
            name=name,
            password_hash=generate_password_hash(password),
            is_teacher=is_teacher
        )
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['is_teacher'] = user.is_teacher
            if user.is_teacher:
                return redirect(url_for('teacher_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid email or password.')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.')
    return redirect(url_for('index'))

# ==================== TEACHER ROUTES ====================

@app.route('/teacher/dashboard')
@teacher_required
def teacher_dashboard():
    user = User.query.get(session['user_id'])
    classes = Class.query.filter_by(teacher_id=user.id).all()
    return render_template('teacher/dashboard.html', classes=classes, user=user)

@app.route('/teacher/class/create', methods=['GET', 'POST'])
@teacher_required
def create_class():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('Class name is required.')
            return redirect(url_for('create_class'))
        
        join_code = generate_code(6)
        while Class.query.filter_by(join_code=join_code).first():
            join_code = generate_code(6)
        
        new_class = Class(
            name=name,
            join_code=join_code,
            teacher_id=session['user_id']
        )
        db.session.add(new_class)
        db.session.commit()
        
        flash(f'Class created! Join code: {join_code}')
        return redirect(url_for('teacher_dashboard'))
    
    return render_template('teacher/create_class.html')

@app.route('/teacher/class/<int:class_id>')
@teacher_required
def view_class(class_id):
    class_obj = Class.query.get_or_404(class_id)
    if class_obj.teacher_id != session['user_id']:
        flash('Access denied.')
        return redirect(url_for('teacher_dashboard'))
    
    quizzes = Quiz.query.filter_by(class_id=class_id).all()
    students = [enrollment.student for enrollment in class_obj.enrollments]
    return render_template(
        'teacher/view_class.html',
        class_obj=class_obj,
        quizzes=quizzes,
        students=students
    )

@app.route('/teacher/class/<int:class_id>/quiz/create', methods=['GET', 'POST'])
@teacher_required
def create_quiz(class_id):
    class_obj = Class.query.get_or_404(class_id)
    if class_obj.teacher_id != session['user_id']:
        flash('Access denied.')
        return redirect(url_for('teacher_dashboard'))
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        max_attempts_raw = request.form.get('max_attempts', '').strip()
        if not title:
            flash('Quiz title is required.')
            return redirect(url_for('create_quiz', class_id=class_id))
        try:
            points_first, points_second, points_third, points_fourth = parse_scoring_scheme(request.form)
        except ValueError as exc:
            flash(str(exc))
            return redirect(url_for('create_quiz', class_id=class_id))

        max_attempts = None
        if max_attempts_raw:
            try:
                max_attempts = int(max_attempts_raw)
            except ValueError:
                flash('Maximum attempts must be a whole number.')
                return redirect(url_for('create_quiz', class_id=class_id))
            if max_attempts < 1:
                flash('Maximum attempts must be at least 1.')
                return redirect(url_for('create_quiz', class_id=class_id))
        
        join_code = generate_code(6)
        while Quiz.query.filter_by(join_code=join_code).first():
            join_code = generate_code(6)
        
        quiz = Quiz(
            title=title,
            join_code=join_code,
            class_id=class_id,
            max_attempts=max_attempts,
            points_first_try=points_first,
            points_second_try=points_second,
            points_third_try=points_third,
            points_fourth_try=points_fourth
        )
        db.session.add(quiz)
        db.session.commit()
        
        flash(f'Quiz created! Join code: {join_code}')
        return redirect(url_for('edit_quiz', quiz_id=quiz.id))
    
    return render_template('teacher/create_quiz.html', class_obj=class_obj)

@app.route('/teacher/quiz/<int:quiz_id>/edit', methods=['GET', 'POST'])
@teacher_required
def edit_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.class_obj.teacher_id != session['user_id']:
        flash('Access denied.')
        return redirect(url_for('teacher_dashboard'))
    
    if request.method == 'POST':
        # Add question
        question_text = request.form.get('question_text', '').strip()
        option_a = request.form.get('option_a', '').strip()
        option_b = request.form.get('option_b', '').strip()
        option_c = request.form.get('option_c', '').strip()
        option_d = request.form.get('option_d', '').strip()
        correct_answer = request.form.get('correct_answer', '').strip().upper()
        explanation = request.form.get('explanation', '').strip()
        
        if not all([question_text, option_a, option_b, option_c, option_d, correct_answer, explanation]):
            flash('All fields are required for a question.')
            return redirect(url_for('edit_quiz', quiz_id=quiz_id))
        
        if correct_answer not in ['A', 'B', 'C', 'D']:
            flash('Correct answer must be A, B, C, or D.')
            return redirect(url_for('edit_quiz', quiz_id=quiz_id))
        
        question = Question(
            quiz_id=quiz_id,
            question_text=question_text,
            option_a=option_a,
            option_b=option_b,
            option_c=option_c,
            option_d=option_d,
            correct_answer=correct_answer,
            explanation=explanation,
            order_num=len(quiz.questions)
        )
        db.session.add(question)
        db.session.commit()
        
        flash('Question added successfully!')
        return redirect(url_for('edit_quiz', quiz_id=quiz_id))
    
    questions = Question.query.filter_by(quiz_id=quiz_id).order_by(Question.order_num).all()
    source_quizzes = Quiz.query.join(Class).filter(
        Class.teacher_id == session['user_id'],
        Quiz.id != quiz.id
    ).order_by(Quiz.title).all()
    source_questions = Question.query.filter(
        Question.quiz_id.in_([q.id for q in source_quizzes])
    ).order_by(Question.quiz_id, Question.order_num).all() if source_quizzes else []
    teacher_classes = Class.query.filter_by(teacher_id=session['user_id']).order_by(Class.name).all()
    return render_template(
        'teacher/edit_quiz.html',
        quiz=quiz,
        questions=questions,
        source_quizzes=source_quizzes,
        source_questions=source_questions,
        teacher_classes=teacher_classes
    )

@app.route('/teacher/question/<int:question_id>/delete', methods=['POST'])
@teacher_required
def delete_question(question_id):
    question = Question.query.get_or_404(question_id)
    quiz_id = question.quiz_id
    if question.quiz.class_obj.teacher_id != session['user_id']:
        flash('Access denied.')
        return redirect(url_for('teacher_dashboard'))
    
    db.session.delete(question)
    db.session.flush()
    normalize_question_order(quiz_id)
    db.session.commit()
    flash('Question deleted.')
    return redirect(url_for('edit_quiz', quiz_id=quiz_id))

@app.route('/teacher/question/<int:question_id>/edit', methods=['GET', 'POST'])
@teacher_required
def edit_question(question_id):
    question = Question.query.get_or_404(question_id)
    quiz = question.quiz
    
    if quiz.class_obj.teacher_id != session['user_id']:
        flash('Access denied.')
        return redirect(url_for('teacher_dashboard'))
    
    if request.method == 'POST':
        question_text = request.form.get('question_text', '').strip()
        option_a = request.form.get('option_a', '').strip()
        option_b = request.form.get('option_b', '').strip()
        option_c = request.form.get('option_c', '').strip()
        option_d = request.form.get('option_d', '').strip()
        correct_answer = request.form.get('correct_answer', '').strip().upper()
        explanation = request.form.get('explanation', '').strip()
        
        if not all([question_text, option_a, option_b, option_c, option_d, correct_answer, explanation]):
            flash('All fields are required.')
            return redirect(url_for('edit_question', question_id=question_id))
        
        if correct_answer not in ['A', 'B', 'C', 'D']:
            flash('Correct answer must be A, B, C, or D.')
            return redirect(url_for('edit_question', question_id=question_id))
        
        question.question_text = question_text
        question.option_a = option_a
        question.option_b = option_b
        question.option_c = option_c
        question.option_d = option_d
        question.correct_answer = correct_answer
        question.explanation = explanation
        db.session.commit()
        
        flash('Question updated successfully!')
        return redirect(url_for('edit_quiz', quiz_id=quiz.id))
    
    return render_template('teacher/edit_question.html', question=question, quiz=quiz)

@app.route('/teacher/question/<int:question_id>/move', methods=['POST'])
@teacher_required
def move_question(question_id):
    question = Question.query.get_or_404(question_id)
    quiz = question.quiz
    if quiz.class_obj.teacher_id != session['user_id']:
        flash('Access denied.')
        return redirect(url_for('teacher_dashboard'))

    direction = request.form.get('direction', '').strip().lower()
    questions = Question.query.filter_by(quiz_id=quiz.id).order_by(Question.order_num, Question.id).all()
    index_map = {q.id: idx for idx, q in enumerate(questions)}
    current_index = index_map[question.id]

    if direction == 'up' and current_index > 0:
        other = questions[current_index - 1]
    elif direction == 'down' and current_index < len(questions) - 1:
        other = questions[current_index + 1]
    else:
        return redirect(url_for('edit_quiz', quiz_id=quiz.id))

    question.order_num, other.order_num = other.order_num, question.order_num
    normalize_question_order(quiz.id)
    db.session.commit()
    return redirect(url_for('edit_quiz', quiz_id=quiz.id))

@app.route('/teacher/quiz/<int:quiz_id>/settings', methods=['POST'])
@teacher_required
def update_quiz_settings(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.class_obj.teacher_id != session['user_id']:
        flash('Access denied.')
        return redirect(url_for('teacher_dashboard'))

    max_attempts_raw = request.form.get('max_attempts', '').strip()
    try:
        points_first, points_second, points_third, points_fourth = parse_scoring_scheme(request.form)
    except ValueError as exc:
        flash(str(exc))
        return redirect(url_for('edit_quiz', quiz_id=quiz.id))

    max_attempts = None
    if max_attempts_raw:
        try:
            max_attempts = int(max_attempts_raw)
        except ValueError:
            flash('Maximum attempts must be a whole number.')
            return redirect(url_for('edit_quiz', quiz_id=quiz.id))
        if max_attempts < 1:
            flash('Maximum attempts must be at least 1.')
            return redirect(url_for('edit_quiz', quiz_id=quiz.id))

    quiz.max_attempts = max_attempts
    quiz.points_first_try = points_first
    quiz.points_second_try = points_second
    quiz.points_third_try = points_third
    quiz.points_fourth_try = points_fourth
    db.session.commit()
    flash('Quiz settings updated.')
    return redirect(url_for('edit_quiz', quiz_id=quiz.id))

@app.route('/teacher/quiz/<int:quiz_id>/question/copy', methods=['POST'])
@teacher_required
def copy_question_into_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.class_obj.teacher_id != session['user_id']:
        flash('Access denied.')
        return redirect(url_for('teacher_dashboard'))

    source_question_id = request.form.get('source_question_id', type=int)
    source_question = Question.query.get_or_404(source_question_id)
    if source_question.quiz.class_obj.teacher_id != session['user_id']:
        flash('Access denied.')
        return redirect(url_for('edit_quiz', quiz_id=quiz.id))

    if source_question.quiz_id == quiz.id:
        flash('Select a question from a different quiz.')
        return redirect(url_for('edit_quiz', quiz_id=quiz.id))

    new_question = Question(
        quiz_id=quiz.id,
        question_text=source_question.question_text,
        option_a=source_question.option_a,
        option_b=source_question.option_b,
        option_c=source_question.option_c,
        option_d=source_question.option_d,
        correct_answer=source_question.correct_answer,
        explanation=source_question.explanation,
        order_num=Question.query.filter_by(quiz_id=quiz.id).count()
    )
    db.session.add(new_question)
    db.session.commit()
    flash('Question copied into quiz.')
    return redirect(url_for('edit_quiz', quiz_id=quiz.id))

@app.route('/teacher/quiz/<int:quiz_id>/copy', methods=['POST'])
@teacher_required
def copy_quiz(quiz_id):
    source_quiz = Quiz.query.get_or_404(quiz_id)
    if source_quiz.class_obj.teacher_id != session['user_id']:
        flash('Access denied.')
        return redirect(url_for('teacher_dashboard'))

    target_class_id = request.form.get('target_class_id', type=int)
    target_class = Class.query.get_or_404(target_class_id)
    if target_class.teacher_id != session['user_id']:
        flash('Access denied.')
        return redirect(url_for('teacher_dashboard'))

    title_suffix = request.form.get('title_suffix', '').strip()
    copied_title = source_quiz.title if not title_suffix else f'{source_quiz.title} {title_suffix}'

    join_code = generate_code(6)
    while Quiz.query.filter_by(join_code=join_code).first():
        join_code = generate_code(6)

    copied_quiz = Quiz(
        title=copied_title,
        join_code=join_code,
        class_id=target_class.id,
        max_attempts=source_quiz.max_attempts,
        points_first_try=source_quiz.points_first_try,
        points_second_try=source_quiz.points_second_try,
        points_third_try=source_quiz.points_third_try,
        points_fourth_try=source_quiz.points_fourth_try,
    )
    db.session.add(copied_quiz)
    db.session.flush()

    source_questions = Question.query.filter_by(quiz_id=source_quiz.id).order_by(Question.order_num).all()
    for idx, src in enumerate(source_questions):
        db.session.add(Question(
            quiz_id=copied_quiz.id,
            question_text=src.question_text,
            option_a=src.option_a,
            option_b=src.option_b,
            option_c=src.option_c,
            option_d=src.option_d,
            correct_answer=src.correct_answer,
            explanation=src.explanation,
            order_num=idx
        ))
    db.session.commit()
    flash(f'Copied quiz to {target_class.name}.')
    return redirect(url_for('edit_quiz', quiz_id=copied_quiz.id))

@app.route('/teacher/analytics')
@teacher_required
def analytics_dashboard():
    user = User.query.get(session['user_id'])
    classes = Class.query.filter_by(teacher_id=user.id).all()
    return render_template('teacher/analytics.html', classes=classes)

@app.route('/teacher/analytics/quiz/<int:quiz_id>/csv')
@teacher_required
def download_quiz_csv(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.class_obj.teacher_id != session['user_id']:
        flash('Access denied.')
        return redirect(url_for('analytics_dashboard'))
    
    anonymize = request.args.get('anonymize') == 'true'
    
    # Create CSV
    output = StringIO()
    writer = csv.writer(output)
    
    # Headers
    headers = ['attempt_id', 'student_id' if anonymize else 'student_name', 
               'student_email' if not anonymize else '', 'attempt_number', 
               'total_score', 'max_score', 'start_time', 'end_time', 'duration_seconds']
    writer.writerow([h for h in headers if h])
    
    attempts = QuizAttempt.query.filter_by(quiz_id=quiz_id).order_by(QuizAttempt.started_at).all()
    
    for attempt in attempts:
        duration = (attempt.completed_at - attempt.started_at).total_seconds() if attempt.completed_at else None
        row = [
            attempt.id,
            f'student_{attempt.student_id}' if anonymize else attempt.student.name,
        ]
        if not anonymize:
            row.append(attempt.student.email)
        row.extend([
            attempt.attempt_number,
            attempt.score,
            len(quiz.questions) * quiz.max_points_per_question,
            attempt.started_at.isoformat(),
            attempt.completed_at.isoformat() if attempt.completed_at else '',
            duration if duration else ''
        ])
        writer.writerow(row)
    
    output.seek(0)
    filename = f'quiz_{quiz_id}_{"anonymized" if anonymize else "named"}.csv'
    
    return send_file(
        BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )

@app.route('/teacher/analytics/class/<int:class_id>/csv')
@teacher_required
def download_class_csv(class_id):
    class_obj = Class.query.get_or_404(class_id)
    if class_obj.teacher_id != session['user_id']:
        flash('Access denied.')
        return redirect(url_for('analytics_dashboard'))
    
    anonymize = request.args.get('anonymize') == 'true'
    
    output = StringIO()
    writer = csv.writer(output)
    
    headers = ['student_id' if anonymize else 'student_name',
               'student_email' if not anonymize else '',
               'quiz_title', 'attempts_count', 'best_score', 'avg_score']
    writer.writerow([h for h in headers if h])
    
    # Get all students in class
    enrollments = class_obj.enrollments
    
    for enrollment in enrollments:
        student = enrollment.student
        for quiz in class_obj.quizzes:
            attempts = QuizAttempt.query.filter_by(quiz_id=quiz.id, student_id=student.id).all()
            if attempts:
                scores = [a.score for a in attempts]
                row = [
                    f'student_{student.id}' if anonymize else student.name,
                ]
                if not anonymize:
                    row.append(student.email)
                row.extend([
                    quiz.title,
                    len(attempts),
                    max(scores),
                    sum(scores) / len(scores)
                ])
                writer.writerow(row)
    
    output.seek(0)
    filename = f'class_{class_id}_{"anonymized" if anonymize else "named"}.csv'
    
    return send_file(
        BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )

@app.route('/teacher/analytics/class/<int:class_id>/scratch-events/csv')
@teacher_required
def download_class_scratch_events_csv(class_id):
    class_obj = Class.query.get_or_404(class_id)
    if class_obj.teacher_id != session['user_id']:
        flash('Access denied.')
        return redirect(url_for('analytics_dashboard'))

    anonymize = request.args.get('anonymize') == 'true'

    output = StringIO()
    writer = csv.writer(output)
    headers = [
        'event_id', 'class_id', 'class_name', 'quiz_id', 'quiz_title', 'attempt_id',
        'student_id' if anonymize else 'student_name', 'question_id', 'question_text',
        'scratch_order', 'scratched_option', 'is_correct', 'timestamp', 'time_since_question_start'
    ]
    writer.writerow([h for h in headers if h])

    quiz_ids = [quiz.id for quiz in class_obj.quizzes]
    if quiz_ids:
        attempts = QuizAttempt.query.filter(QuizAttempt.quiz_id.in_(quiz_ids)).all()
        for attempt in attempts:
            for q_attempt in attempt.question_attempts:
                for event in q_attempt.scratch_events:
                    time_delta = (event.timestamp - q_attempt.started_at).total_seconds()
                    row = [
                        event.id,
                        class_obj.id,
                        class_obj.name,
                        attempt.quiz_id,
                        attempt.quiz.title,
                        attempt.id,
                        f'student_{attempt.student_id}' if anonymize else attempt.student.name,
                        q_attempt.question_id,
                        q_attempt.question.question_text[:50] + '...' if len(q_attempt.question.question_text) > 50 else q_attempt.question.question_text,
                        event.scratch_order,
                        event.scratched_option,
                        event.is_correct,
                        event.timestamp.isoformat(),
                        time_delta
                    ]
                    writer.writerow(row)

    output.seek(0)
    filename = f'class_{class_id}_scratch_events_{"anonymized" if anonymize else "named"}.csv'
    return send_file(
        BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )

@app.route('/teacher/analytics/scratch-events/<int:quiz_id>/csv')
@teacher_required
def download_scratch_events_csv(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.class_obj.teacher_id != session['user_id']:
        flash('Access denied.')
        return redirect(url_for('analytics_dashboard'))
    
    anonymize = request.args.get('anonymize') == 'true'
    
    output = StringIO()
    writer = csv.writer(output)
    
    headers = ['event_id', 'attempt_id', 'student_id' if anonymize else 'student_name',
               'question_id', 'question_text', 'scratch_order', 'scratched_option',
               'is_correct', 'timestamp', 'time_since_question_start']
    writer.writerow([h for h in headers if h])
    
    attempts = QuizAttempt.query.filter_by(quiz_id=quiz_id).all()
    
    for attempt in attempts:
        for q_attempt in attempt.question_attempts:
            for event in q_attempt.scratch_events:
                time_delta = (event.timestamp - q_attempt.started_at).total_seconds()
                row = [
                    event.id,
                    attempt.id,
                    f'student_{attempt.student_id}' if anonymize else attempt.student.name,
                    q_attempt.question_id,
                    q_attempt.question.question_text[:50] + '...' if len(q_attempt.question.question_text) > 50 else q_attempt.question.question_text,
                    event.scratch_order,
                    event.scratched_option,
                    event.is_correct,
                    event.timestamp.isoformat(),
                    time_delta
                ]
                writer.writerow(row)
    
    output.seek(0)
    filename = f'scratch_events_{quiz_id}_{"anonymized" if anonymize else "named"}.csv'
    
    return send_file(
        BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )

# ==================== STUDENT ROUTES ====================

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    user = User.query.get(session['user_id'])
    if user.is_teacher:
        return redirect(url_for('teacher_dashboard'))
    
    enrollments = user.enrollments
    attempts = QuizAttempt.query.filter_by(student_id=user.id).all()
    attempt_counts = {}
    in_progress_attempt_ids = set()
    latest_incomplete_attempt_by_quiz = {}
    best_scores = {}
    for attempt in attempts:
        attempt_counts[attempt.quiz_id] = attempt_counts.get(attempt.quiz_id, 0) + 1
        if not attempt.completed_at:
            in_progress_attempt_ids.add(attempt.quiz_id)
            existing = latest_incomplete_attempt_by_quiz.get(attempt.quiz_id)
            if existing is None or attempt.started_at > existing.started_at:
                latest_incomplete_attempt_by_quiz[attempt.quiz_id] = attempt
        if attempt.completed_at:
            previous_best = best_scores.get(attempt.quiz_id)
            if previous_best is None or attempt.score > previous_best:
                best_scores[attempt.quiz_id] = attempt.score
    return render_template(
        'student/dashboard.html',
        enrollments=enrollments,
        user=user,
        attempt_counts=attempt_counts,
        in_progress_attempt_ids=in_progress_attempt_ids,
        latest_incomplete_attempt_by_quiz=latest_incomplete_attempt_by_quiz,
        best_scores=best_scores
    )

@app.route('/student/join/class', methods=['GET', 'POST'])
@login_required
def join_class():
    if request.method == 'POST':
        join_code = request.form.get('join_code', '').strip().upper()
        class_obj = Class.query.filter_by(join_code=join_code).first()
        
        if not class_obj:
            flash('Invalid class join code.')
            return redirect(url_for('join_class'))
        
        user = User.query.get(session['user_id'])
        if class_obj in [e.class_obj for e in user.enrollments]:
            flash('You are already enrolled in this class.')
            return redirect(url_for('student_dashboard'))
        
        enrollment = Enrollment(student_id=user.id, class_id=class_obj.id)
        db.session.add(enrollment)
        db.session.commit()
        
        flash(f'Successfully joined class: {class_obj.name}')
        return redirect(url_for('student_dashboard'))
    
    return render_template('student/join_class.html')

@app.route('/student/join/quiz', methods=['GET', 'POST'])
@login_required
def join_quiz():
    if request.method == 'POST':
        join_code = request.form.get('join_code', '').strip().upper()
        quiz = Quiz.query.filter_by(join_code=join_code).first()
        
        if not quiz:
            flash('Invalid quiz join code.')
            return redirect(url_for('join_quiz'))
        
        new_attempt, error = create_quiz_attempt(quiz, session['user_id'])
        if error:
            flash(error)
            return redirect(url_for('student_dashboard'))
        return redirect(url_for('take_quiz', attempt_id=new_attempt.id))
    
    return render_template('student/join_quiz.html')

@app.route('/student/quiz/<int:quiz_id>/start', methods=['POST'])
@login_required
def start_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if session.get('is_teacher'):
        flash('Student access required.')
        return redirect(url_for('teacher_dashboard'))

    new_attempt, error = create_quiz_attempt(quiz, session['user_id'])
    if error:
        flash(error)
        return redirect(url_for('student_dashboard'))
    return redirect(url_for('take_quiz', attempt_id=new_attempt.id))

@app.route('/student/quiz/<int:attempt_id>')
@login_required
def take_quiz(attempt_id):
    attempt = QuizAttempt.query.get_or_404(attempt_id)
    
    if attempt.student_id != session['user_id']:
        flash('Access denied.')
        return redirect(url_for('student_dashboard'))
    
    quiz = attempt.quiz
    questions = Question.query.filter_by(quiz_id=quiz.id).order_by(Question.order_num).all()
    
    # Initialize question attempts if needed
    for question in questions:
        existing = QuestionAttempt.query.filter_by(
            quiz_attempt_id=attempt_id,
            question_id=question.id
        ).first()
        if not existing:
            q_attempt = QuestionAttempt(
                quiz_attempt_id=attempt_id,
                question_id=question.id,
                started_at=datetime.now(timezone.utc)
            )
            db.session.add(q_attempt)
    db.session.commit()
    
    return render_template('student/take_quiz.html', attempt=attempt, quiz=quiz, questions=questions)

@app.route('/api/scratch', methods=['POST'])
@login_required
def scratch():
    """Handle scratch events"""
    data = request.json
    attempt_id = data.get('attempt_id')
    question_id = data.get('question_id')
    option = data.get('option', '').upper()
    
    attempt = QuizAttempt.query.get_or_404(attempt_id)
    if attempt.student_id != session['user_id']:
        return jsonify({'error': 'Access denied'}), 403
    
    question = Question.query.get_or_404(question_id)
    q_attempt = QuestionAttempt.query.filter_by(
        quiz_attempt_id=attempt_id,
        question_id=question_id
    ).first()
    
    if not q_attempt:
        return jsonify({'error': 'Question attempt not found'}), 404
    
    if q_attempt.is_complete:
        return jsonify({'error': 'Question already completed'}), 400
    
    # Count existing scratches
    scratch_count = ScratchEvent.query.filter_by(question_attempt_id=q_attempt.id).count()
    
    if scratch_count >= 4:
        return jsonify({'error': 'All options already scratched'}), 400
    
    # Check if this option was already scratched
    existing = ScratchEvent.query.filter_by(
        question_attempt_id=q_attempt.id,
        scratched_option=option
    ).first()
    
    if existing:
        return jsonify({'error': 'Option already scratched'}), 400
    
    is_correct = (option == question.correct_answer)
    
    # Record scratch event
    scratch_event = ScratchEvent(
        question_attempt_id=q_attempt.id,
        scratched_option=option,
        is_correct=is_correct,
        scratch_order=scratch_count + 1,
        timestamp=datetime.now(timezone.utc)
    )
    db.session.add(scratch_event)
    
    # Update question attempt
    scoring_scheme = attempt.quiz.scoring_scheme

    if is_correct:
        q_attempt.is_complete = True
        q_attempt.points_earned = scoring_scheme[scratch_count]
        q_attempt.completed_at = datetime.now(timezone.utc)
        q_attempt.attempts_before_correct = scratch_count
    
    # Track last activity
    attempt.last_activity_at = datetime.now(timezone.utc)
    
    db.session.commit()
    
    # Calculate time to first scratch and time to correct
    time_to_first = None
    time_to_correct = None
    
    if scratch_count == 0:  # First scratch
        time_to_first = (scratch_event.timestamp - q_attempt.started_at).total_seconds()
    
    if is_correct:
        time_to_correct = (scratch_event.timestamp - q_attempt.started_at).total_seconds()
    
    response = {
        'is_correct': is_correct,
        'points_remaining': scoring_scheme[min(scratch_count + 1, 3)] if not is_correct else scoring_scheme[scratch_count],
        'explanation': question.explanation if is_correct else None,
        'scratch_count': scratch_count + 1
    }
    
    # Check if quiz is complete
    total_questions = Question.query.filter_by(quiz_id=attempt.quiz_id).count()
    completed_questions = QuestionAttempt.query.filter_by(
        quiz_attempt_id=attempt_id,
        is_complete=True
    ).count()
    
    if completed_questions == total_questions and not attempt.completed_at:
        attempt.completed_at = datetime.now(timezone.utc)
        # Calculate total score
        total_score = db.session.query(db.func.sum(QuestionAttempt.points_earned)).filter_by(
            quiz_attempt_id=attempt_id
        ).scalar() or 0
        attempt.score = total_score
        db.session.commit()
        response['quiz_complete'] = True
    
    return jsonify(response)

@app.route('/api/quiz-attempt/<int:attempt_id>/state', methods=['GET'])
@login_required
def get_quiz_attempt_state(attempt_id):
    """Get the current state of a quiz attempt (used to restore state on page reload)"""
    attempt = QuizAttempt.query.get_or_404(attempt_id)
    if attempt.student_id != session['user_id']:
        return jsonify({'error': 'Access denied'}), 403
    
    attempt_data = {
        'attempt_id': attempt.id,
        'quiz_complete': attempt.completed_at is not None,
        'questions': {}
    }
    
    for q_attempt in attempt.question_attempts:
        attempt_data['questions'][str(q_attempt.question_id)] = {
            'is_complete': q_attempt.is_complete,
            'scratches': [
                {
                    'option': event.scratched_option,
                    'is_correct': event.is_correct
                }
                for event in q_attempt.scratch_events
            ],
            'points_remaining': q_attempt.question.quiz.scoring_scheme[len(q_attempt.scratch_events)] if len(q_attempt.scratch_events) < 4 else 0
        }
    
    return jsonify(attempt_data)

@app.route('/student/results/<int:attempt_id>')
@login_required
def view_results(attempt_id):
    attempt = QuizAttempt.query.get_or_404(attempt_id)
    
    if attempt.student_id != session['user_id']:
        flash('Access denied.')
        return redirect(url_for('student_dashboard'))
    
    if not attempt.completed_at:
        flash('Quiz not yet completed.')
        return redirect(url_for('take_quiz', attempt_id=attempt_id))
    
    quiz = attempt.quiz
    questions = Question.query.filter_by(quiz_id=quiz.id).order_by(Question.order_num).all()
    max_score = len(questions) * quiz.max_points_per_question
    
    return render_template('student/results.html', attempt=attempt, quiz=quiz, 
                         questions=questions, max_score=max_score)

# ==================== INIT DATABASE ====================

@app.cli.command()
def init_db():
    """Initialize the database"""
    db.create_all()
    ensure_schema_updates()
    print('Database initialized.')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        ensure_schema_updates()
    app.run(debug=True, host='0.0.0.0', port=5001)
