# IF-AT Research Prototype

A research-grade digital implementation of Immediate Feedback Assessment Technique (IF-AT) scratch cards for physics education research.

## Features

### Teacher Features
- Create multiple classes with unique join codes
- Create quizzes within classes with unique join codes
- Add questions with 4 multiple-choice options
- Provide detailed explanations for each question
- Access comprehensive learning analytics
- Export data in CSV format (named or anonymized)

### Student Features
- Join classes using join codes
- Take quizzes multiple times (retakes allowed)
- Experience realistic IF-AT scratch card interface
- Receive immediate feedback with each scratch
- View detailed results after completion

### Research Data Collection
- Complete scratch event tracking (order, timing, correctness)
- Time-to-first-scratch and time-to-correct metrics
- Points earned per question
- Number of incorrect attempts before correct answer
- Per-student, per-quiz, and per-class analytics
- Anonymized export options with stable student IDs

## Tech Stack

- **Backend**: Python 3.11+, Flask
- **Database**: PostgreSQL (production), SQLite (local testing)
- **Frontend**: HTML, CSS, Vanilla JavaScript
- **Deployment**: Render-ready with Gunicorn

## Local Setup

### Prerequisites
- Python 3.11 or higher
- pip

### Installation

1. Clone or download this project

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set environment variables (optional for local testing):
```bash
export SECRET_KEY='your-secret-key-here'
export DATABASE_URL='sqlite:///ifat.db'  # Default if not set
```

5. Initialize the database:
```bash
python app.py
```
The database will be created automatically on first run.

6. Run the application:
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Deployment to Render

### Prerequisites
- GitHub account
- Render account (free tier works)

### Steps

1. Push your code to GitHub

2. Create a new PostgreSQL database on Render:
   - Go to Render Dashboard
   - Click "New +" → "PostgreSQL"
   - Name it (e.g., "ifat-db")
   - Select region and plan (Free tier works)
   - Click "Create Database"
   - Copy the "Internal Database URL"

3. Create a new Web Service on Render:
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Configure:
     - **Name**: ifat-prototype (or your choice)
     - **Environment**: Python 3
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `gunicorn app:app`
   
4. Add Environment Variables:
   - Click "Environment" tab
   - Add:
     - `SECRET_KEY`: Generate a secure random string
     - `DATABASE_URL`: Paste the Internal Database URL from step 2
   
5. Deploy:
   - Click "Create Web Service"
   - Wait for build and deployment
   - Your app will be live at `https://your-app-name.onrender.com`

### Generate a Secure Secret Key

```python
import secrets
print(secrets.token_hex(32))
```

## Database Schema

### Users
- Email/password authentication (passwords hashed)
- Role: Teacher or Student

### Classes
- Created by teachers
- 6-character alphanumeric join code
- Multiple students can enroll

### Quizzes
- Belong to classes
- 6-character alphanumeric join code
- Multiple questions per quiz
- Students can attempt multiple times

### Questions
- 4 multiple-choice options (A-D)
- One correct answer
- Detailed explanation

### Quiz Attempts
- Tracks each student attempt
- Stores score and timing data
- Retakes allowed

### Question Attempts
- Tracks per-question performance
- Points earned (0-4)
- Number of incorrect attempts
- Completion timing

### Scratch Events
- Individual scratch recording
- Order, option, correctness, timestamp
- Used for detailed learning analytics

## Research Data Exports

### CSV Export Types

1. **Per-Quiz Performance**
   - Attempt-level data
   - Score, timing, attempt number
   - Named or anonymized

2. **Per-Class Summary**
   - Student-level aggregations
   - Best score, average score, attempts
   - Named or anonymized

3. **Scratch Events (Raw Data)**
   - Every individual scratch
   - Time since question start
   - Order and correctness
   - Named or anonymized

All anonymized exports use stable student IDs (e.g., `student_123`) that remain consistent across exports.

## Usage Guide

### For Teachers

1. Register as a Teacher
2. Create a Class (you'll receive a join code)
3. Share the class join code with students
4. Create a Quiz within the class
5. Add questions to the quiz
6. Share the quiz join code when ready
7. Access Analytics to download CSV data

### For Students

1. Register as a Student
2. Join a class using the teacher's class join code
3. Join a quiz using the teacher's quiz join code
4. Complete the quiz by scratching answers
5. View your results
6. Retake if desired

## Scratch Card Mechanics

- Each question starts with 4 points
- Options are hidden behind gray circles (Scantron-style)
- Click to "scratch" and reveal
- Each incorrect scratch: ❌ shown, 1 point deducted
- Correct scratch: ✅ shown, explanation displayed, remaining points awarded
- Question locks after correct answer found

## Capacity

- Designed for ~100 students per class
- Supports multiple concurrent users
- All data persisted in database

## Security Notes

- Passwords are hashed using Werkzeug's security utilities
- Session-based authentication
- CSRF protection through Flask
- Environment variables for secrets
- For production: Use strong SECRET_KEY and HTTPS

## Limitations (by Design)

This is a research prototype, not a production system:
- No password reset functionality
- No email verification
- Minimal input validation
- No advanced admin controls
- Basic UI (function over aesthetics)

## Support

For issues or questions about the prototype, refer to the code comments or Flask documentation.

## License

This is a research prototype for educational use.
