# IF-AT Prototype Project Structure

```
ifat_prototype/
│
├── app.py                          # Main Flask application with all routes
├── models.py                       # SQLAlchemy database models
├── requirements.txt                # Python dependencies
├── README.md                       # Complete documentation
├── DEPLOYMENT.md                   # Render deployment guide
├── test_app.py                     # Basic functionality tests
├── .gitignore                      # Git ignore rules
│
├── templates/                      # HTML templates
│   ├── base.html                   # Base template with navigation
│   ├── index.html                  # Landing page
│   ├── login.html                  # Login page
│   ├── register.html               # Registration page
│   │
│   ├── teacher/                    # Teacher-specific templates
│   │   ├── dashboard.html          # Teacher dashboard
│   │   ├── create_class.html       # Class creation form
│   │   ├── view_class.html         # Class details and quizzes
│   │   ├── create_quiz.html        # Quiz creation form
│   │   ├── edit_quiz.html          # Quiz editor with question management
│   │   └── analytics.html          # Analytics and CSV downloads
│   │
│   └── student/                    # Student-specific templates
│       ├── dashboard.html          # Student dashboard
│       ├── join_class.html         # Class join form
│       ├── join_quiz.html          # Quiz join form
│       ├── take_quiz.html          # Interactive quiz with scratch cards
│       └── results.html            # Quiz results display
│
└── static/                         # Static assets
    └── css/
        └── style.css               # All application styles

```

## File Descriptions

### Core Application Files

**app.py** (500+ lines)
- Flask app initialization and configuration
- Authentication routes (login, register, logout)
- Teacher routes (dashboard, class/quiz management)
- Student routes (dashboard, join, take quiz)
- Analytics routes (CSV exports)
- API endpoint for scratch events
- Database initialization

**models.py** (150+ lines)
- User model (authentication, role)
- Class model (teacher's classes)
- Enrollment model (student-class relationship)
- Quiz model (class quizzes)
- Question model (quiz questions with 4 options)
- QuizAttempt model (student quiz attempts)
- QuestionAttempt model (per-question performance)
- ScratchEvent model (individual scratch tracking)

### Templates

**Base Layout**
- `base.html`: Navigation, flash messages, common structure

**Public Templates**
- `index.html`: Landing page with feature overview
- `login.html`: Email/password authentication
- `register.html`: User registration with role selection

**Teacher Templates**
- `dashboard.html`: Class overview and management
- `create_class.html`: New class form
- `view_class.html`: Class details with quiz list
- `create_quiz.html`: New quiz form
- `edit_quiz.html`: Question management interface
- `analytics.html`: CSV export dashboard

**Student Templates**
- `dashboard.html`: Class and attempt overview
- `join_class.html`: Class join code entry
- `join_quiz.html`: Quiz join code entry
- `take_quiz.html`: Interactive IF-AT scratch interface
- `results.html`: Detailed performance breakdown

### Static Files

**style.css** (600+ lines)
- Reset and base styles
- Navigation styling
- Form layouts
- Card components
- Dashboard grids
- Scratch card interface (circles, overlays, reveals)
- Analytics layouts
- Responsive design

### Configuration Files

**requirements.txt**
- Flask 3.0.0
- Flask-SQLAlchemy 3.1.1
- Werkzeug 3.0.1
- psycopg2-binary 2.9.9 (PostgreSQL adapter)
- gunicorn 21.2.0 (production server)

**README.md**
- Complete project overview
- Setup instructions
- Deployment guide
- Usage instructions
- Research data export guide

**DEPLOYMENT.md**
- Step-by-step Render deployment
- Database setup
- Environment variables
- Troubleshooting guide

**.gitignore**
- Python cache files
- Database files
- Environment files
- IDE files

## Key Architecture Decisions

### Database Design
- Normalized schema for research data integrity
- Separate tables for attempts, questions, and scratch events
- Allows detailed learning analytics and CSV exports

### Authentication
- Session-based authentication
- Password hashing with Werkzeug
- Role-based access control (teacher/student)

### Scratch Card Logic
- Frontend: JavaScript handles UI interactions
- Backend: Python validates and records each scratch
- Real-time updates via AJAX to API endpoint
- Locks question after correct answer found

### CSV Exports
- Three export types: quiz performance, class summary, scratch events
- Named and anonymized options
- Stable anonymized IDs per student

### Deployment Strategy
- Environment variables for secrets
- PostgreSQL for production
- SQLite for local development
- Gunicorn WSGI server for Render

## Data Flow Examples

### Student Takes Quiz
1. Student enters quiz join code
2. System creates new QuizAttempt
3. QuestionAttempt records created for each question
4. Student clicks scratch circle
5. JavaScript sends AJAX request to `/api/scratch`
6. Backend validates and records ScratchEvent
7. Response includes correctness, points, explanation
8. Frontend updates UI (reveal, points, lock if correct)
9. When all questions complete, quiz marked complete
10. Student redirects to results page

### Teacher Downloads Analytics
1. Teacher clicks CSV download link
2. System queries relevant attempts/events
3. CSV generated in-memory with pandas-like logic
4. Named or anonymized based on parameter
5. File sent to browser for download
6. No files stored on server

## Extension Points

If you need to extend this prototype:

1. **Additional Question Types**: Add new question models in `models.py`
2. **More Analytics**: Add new CSV export routes in `app.py`
3. **Styling**: Modify `static/css/style.css`
4. **Advanced Features**: Add routes and templates following existing patterns
5. **API Endpoints**: Add to `app.py` following `/api/scratch` pattern

## Testing Checklist

Before deploying:
- [ ] Teacher can register and login
- [ ] Teacher can create class and get join code
- [ ] Teacher can create quiz and add questions
- [ ] Student can register and login
- [ ] Student can join class with join code
- [ ] Student can join quiz with join code
- [ ] Scratch interface works (reveals, points, explanation)
- [ ] Quiz completes after all questions answered
- [ ] Results display correctly
- [ ] Student can retake quiz
- [ ] CSV exports download correctly
- [ ] Anonymized exports show stable IDs
