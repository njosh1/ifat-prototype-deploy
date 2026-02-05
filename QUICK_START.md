# IF-AT Research Prototype - Quick Start Guide

## What You Have

A complete, deployment-ready IF-AT (Immediate Feedback Assessment Technique) scratch card system for physics education research.

## Getting Started Locally (5 minutes)

1. **Install Python 3.11+** if not already installed

2. **Extract and navigate** to the project folder:
   ```bash
   cd ifat_prototype
   ```

3. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the app**:
   ```bash
   python app.py
   ```

6. **Visit**: http://localhost:5000

7. **Create sample data** (optional):
   ```bash
   python create_sample_data.py
   ```
   This creates a demo teacher, student, class, and quiz with 5 physics questions.

## Test the System

### As Teacher:
1. Register at `/register` as Teacher
2. Create a class (get a join code like "ABC123")
3. Create a quiz within that class
4. Add questions with 4 options each
5. Get the quiz join code

### As Student:
1. Register at `/register` as Student  
2. Join class with the class code
3. Join quiz with the quiz code
4. Experience the scratch interface:
   - Click gray circles to scratch
   - Each wrong scratch = ❌ and -1 point
   - Correct scratch = ✅ and explanation shown
5. View results when complete
6. Retake if desired

### Analytics:
1. Login as teacher
2. Go to Analytics
3. Download CSV files (named or anonymized):
   - Quiz performance data
   - Class summaries
   - Raw scratch events with timing

## Deploy to Render (15 minutes)

Follow the detailed guide in **DEPLOYMENT.md**

Quick summary:
1. Push code to GitHub
2. Create PostgreSQL database on Render
3. Create Web Service linked to your repo
4. Add environment variables (SECRET_KEY, DATABASE_URL)
5. Deploy and test!

## Key Files

- **app.py**: All routes and logic
- **models.py**: Database schema
- **templates/**: All HTML files
- **static/css/style.css**: All styling
- **README.md**: Complete documentation
- **DEPLOYMENT.md**: Step-by-step Render deployment
- **PROJECT_STRUCTURE.md**: Detailed architecture

## Research Features

### Data Collected Per Scratch:
- Scratched option (A/B/C/D)
- Is correct (True/False)
- Scratch order (1, 2, 3, 4)
- Timestamp
- Time since question started

### Aggregated Per Question:
- Points earned (0-4)
- Attempts before correct
- Time to first scratch
- Time to correct answer

### Per Quiz Attempt:
- Total score
- Completion time
- Attempt number (retakes tracked separately)

### CSV Exports:
- **Quiz Performance**: Per-attempt scores and timing
- **Class Summary**: Aggregated per-student stats
- **Scratch Events**: Every single scratch with timestamps

All exports available in:
- **Named** format: Real student names/emails
- **Anonymized** format: Stable student IDs (e.g., student_42)

## Capacity

Designed for:
- ~100 students per class
- Multiple classes per teacher
- Unlimited quiz retakes
- All data persisted in database

## Support

- **Questions?** See README.md
- **Deployment issues?** See DEPLOYMENT.md  
- **Architecture questions?** See PROJECT_STRUCTURE.md

## Sample Physics Questions Included

If you run `create_sample_data.py`, you'll get 5 sample physics questions about:
- Newton's Second Law (F=ma)
- Newton's First Law (Inertia)
- Newton's Third Law (Action-Reaction)
- Momentum calculation
- SI units for force

## Next Steps

1. **Test locally** with sample data
2. **Customize** questions for your research
3. **Deploy to Render** for online access
4. **Pilot test** with a small group
5. **Collect data** and export CSVs
6. **Analyze** in your statistical software of choice

## Research Use

This prototype is specifically designed for learning analytics research:
- Tracks everything needed for IF-AT research
- Exports clean CSV files
- Maintains anonymization options
- Supports multiple attempts per student
- Records granular timing data

Perfect for studying:
- Test-enhanced learning
- Immediate feedback effects
- Collaborative assessment
- Mistake pattern analysis
- Time-on-task correlations

---

Built for clarity, correctness, and research data quality.
No over-engineering. Just what you need for classroom testing and learning analytics.
