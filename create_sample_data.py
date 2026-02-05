"""
Sample data generator for testing the IF-AT prototype
This creates a teacher, class, quiz with sample physics questions
"""

from app import app, db
from models import User, Class, Quiz, Question
from werkzeug.security import generate_password_hash
import secrets
import string

def generate_code(length=6):
    return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(length))

def create_sample_data():
    """Create sample teacher, class, and quiz with physics questions"""
    
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        
        # Check if sample teacher already exists
        existing_teacher = User.query.filter_by(email='demo.teacher@ifat.edu').first()
        if existing_teacher:
            print("Sample data already exists. Delete the database to regenerate.")
            return
        
        # Create sample teacher
        teacher = User(
            email='demo.teacher@ifat.edu',
            name='Dr. Demo Teacher',
            password_hash=generate_password_hash('teacher123'),
            is_teacher=True
        )
        db.session.add(teacher)
        db.session.flush()  # Get teacher ID
        
        print(f"✓ Created teacher: {teacher.email} / password: teacher123")
        
        # Create sample class
        class_code = generate_code(6)
        sample_class = Class(
            name='Physics 101 - Spring 2026',
            join_code=class_code,
            teacher_id=teacher.id
        )
        db.session.add(sample_class)
        db.session.flush()
        
        print(f"✓ Created class: {sample_class.name}")
        print(f"  Class join code: {class_code}")
        
        # Create sample quiz
        quiz_code = generate_code(6)
        sample_quiz = Quiz(
            title='Forces and Motion - Chapter 5',
            join_code=quiz_code,
            class_id=sample_class.id
        )
        db.session.add(sample_quiz)
        db.session.flush()
        
        print(f"✓ Created quiz: {sample_quiz.title}")
        print(f"  Quiz join code: {quiz_code}")
        
        # Sample physics questions
        questions = [
            {
                'text': 'A 2 kg object accelerates at 3 m/s². What is the net force acting on it?',
                'options': {
                    'A': '5 N',
                    'B': '6 N',
                    'C': '1.5 N',
                    'D': '8 N'
                },
                'correct': 'B',
                'explanation': 'Using Newton\'s Second Law (F = ma), F = 2 kg × 3 m/s² = 6 N. The net force is directly proportional to both mass and acceleration.'
            },
            {
                'text': 'An object at rest will remain at rest unless acted upon by what?',
                'options': {
                    'A': 'Time',
                    'B': 'Friction',
                    'C': 'An unbalanced force',
                    'D': 'Gravity'
                },
                'correct': 'C',
                'explanation': 'This is Newton\'s First Law of Motion (Law of Inertia). An object maintains its state of motion unless an unbalanced (net) force acts upon it.'
            },
            {
                'text': 'If you push on a wall with 50 N of force, how much force does the wall exert back on you?',
                'options': {
                    'A': '0 N',
                    'B': '25 N',
                    'C': '50 N',
                    'D': '100 N'
                },
                'correct': 'C',
                'explanation': 'Newton\'s Third Law states that for every action, there is an equal and opposite reaction. The wall exerts exactly 50 N back on you.'
            },
            {
                'text': 'A 10 kg object moving at 5 m/s has what momentum?',
                'options': {
                    'A': '2 kg⋅m/s',
                    'B': '15 kg⋅m/s',
                    'C': '50 kg⋅m/s',
                    'D': '0.5 kg⋅m/s'
                },
                'correct': 'C',
                'explanation': 'Momentum (p) = mass × velocity. p = 10 kg × 5 m/s = 50 kg⋅m/s. Momentum is a vector quantity in the direction of velocity.'
            },
            {
                'text': 'What is the SI unit for force?',
                'options': {
                    'A': 'Joule',
                    'B': 'Watt',
                    'C': 'Newton',
                    'D': 'Pascal'
                },
                'correct': 'C',
                'explanation': 'The Newton (N) is the SI unit for force. It is defined as the force required to accelerate 1 kg of mass at 1 m/s². 1 N = 1 kg⋅m/s².'
            }
        ]
        
        # Add questions to quiz
        for i, q_data in enumerate(questions):
            question = Question(
                quiz_id=sample_quiz.id,
                question_text=q_data['text'],
                option_a=q_data['options']['A'],
                option_b=q_data['options']['B'],
                option_c=q_data['options']['C'],
                option_d=q_data['options']['D'],
                correct_answer=q_data['correct'],
                explanation=q_data['explanation'],
                order_num=i
            )
            db.session.add(question)
        
        db.session.commit()
        print(f"✓ Added {len(questions)} sample questions")
        
        # Create sample student
        student = User(
            email='demo.student@ifat.edu',
            name='Demo Student',
            password_hash=generate_password_hash('student123'),
            is_teacher=False
        )
        db.session.add(student)
        db.session.commit()
        
        print(f"✓ Created student: {student.email} / password: student123")
        
        print("\n" + "="*60)
        print("Sample data created successfully!")
        print("="*60)
        print("\nLogin Credentials:")
        print(f"  Teacher: demo.teacher@ifat.edu / teacher123")
        print(f"  Student: demo.student@ifat.edu / student123")
        print("\nJoin Codes:")
        print(f"  Class: {class_code}")
        print(f"  Quiz: {quiz_code}")
        print("\nNext steps:")
        print("1. Login as student")
        print("2. Use class join code to enroll")
        print("3. Use quiz join code to take the quiz")
        print("4. Try the scratch card interface!")

if __name__ == '__main__':
    create_sample_data()
