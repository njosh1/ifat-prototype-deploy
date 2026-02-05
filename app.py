import os
import secrets
import string
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import csv
from io import StringIO, BytesIO

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

# ==================== UTILITIES ====================

def generate_code(length=6):
    """Generate random alphanumeric code"""
    return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(length))

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
    return render_template('teacher/view_class.html', class_obj=class_obj, quizzes=quizzes)

@app.route('/teacher/class/<int:class_id>/quiz/create', methods=['GET', 'POST'])
@teacher_required
def create_quiz(class_id):
    class_obj = Class.query.get_or_404(class_id)
    if class_obj.teacher_id != session['user_id']:
        flash('Access denied.')
        return redirect(url_for('teacher_dashboard'))
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        if not title:
            flash('Quiz title is required.')
            return redirect(url_for('create_quiz', class_id=class_id))
        
        join_code = generate_code(6)
        while Quiz.query.filter_by(join_code=join_code).first():
            join_code = generate_code(6)
        
        quiz = Quiz(
            title=title,
            join_code=join_code,
            class_id=class_id
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
    return render_template('teacher/edit_quiz.html', quiz=quiz, questions=questions)

@app.route('/teacher/question/<int:question_id>/delete', methods=['POST'])
@teacher_required
def delete_question(question_id):
    question = Question.query.get_or_404(question_id)
    quiz_id = question.quiz_id
    if question.quiz.class_obj.teacher_id != session['user_id']:
        flash('Access denied.')
        return redirect(url_for('teacher_dashboard'))
    
    db.session.delete(question)
    db.session.commit()
    flash('Question deleted.')
    return redirect(url_for('edit_quiz', quiz_id=quiz_id))

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
            len(quiz.questions) * 4,
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
    return render_template('student/dashboard.html', enrollments=enrollments, user=user)

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
        
        user = User.query.get(session['user_id'])
        # Check if student is enrolled in the class
        if quiz.class_obj not in [e.class_obj for e in user.enrollments]:
            flash('You must be enrolled in the class to access this quiz.')
            return redirect(url_for('join_class'))
        
        # Create new attempt
        attempt_count = QuizAttempt.query.filter_by(quiz_id=quiz.id, student_id=user.id).count()
        new_attempt = QuizAttempt(
            quiz_id=quiz.id,
            student_id=user.id,
            attempt_number=attempt_count + 1,
            started_at=datetime.now(timezone.utc)
        )
        db.session.add(new_attempt)
        db.session.commit()
        
        return redirect(url_for('take_quiz', attempt_id=new_attempt.id))
    
    return render_template('student/join_quiz.html')

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
    if is_correct:
        q_attempt.is_complete = True
        q_attempt.points_earned = 4 - scratch_count
        q_attempt.completed_at = datetime.now(timezone.utc)
        q_attempt.attempts_before_correct = scratch_count
    
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
        'points_remaining': 4 - scratch_count if not is_correct else 4 - scratch_count,
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
    max_score = len(questions) * 4
    
    return render_template('student/results.html', attempt=attempt, quiz=quiz, 
                         questions=questions, max_score=max_score)

# ==================== INIT DATABASE ====================

@app.cli.command()
def init_db():
    """Initialize the database"""
    db.create_all()
    print('Database initialized.')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5001)
