# Render Deployment Quick Start

## Step 1: Prepare Your Repository

1. Push this code to a GitHub repository
2. Make sure all files are committed, especially:
   - `app.py`
   - `models.py`
   - `requirements.txt`
   - `templates/` folder
   - `static/` folder

## Step 2: Create PostgreSQL Database on Render

1. Go to https://dashboard.render.com
2. Click "New +" → "PostgreSQL"
3. Fill in:
   - **Name**: ifat-database (or your choice)
   - **Database**: ifat_db
   - **User**: (auto-generated)
   - **Region**: Choose closest to you
   - **PostgreSQL Version**: 15 (or latest)
   - **Plan**: Free
4. Click "Create Database"
5. **IMPORTANT**: Copy the "Internal Database URL" from the database info page
   - It looks like: `postgresql://user:password@host/database`

## Step 3: Create Web Service on Render

1. Click "New +" → "Web Service"
2. Connect your GitHub repository
3. Fill in:
   - **Name**: ifat-prototype (or your choice)
   - **Region**: Same as database
   - **Branch**: main (or your branch)
   - **Root Directory**: (leave blank)
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Plan**: Free

## Step 4: Add Environment Variables

In the "Environment" tab, add these variables:

### SECRET_KEY
Generate a secure key in Python:
```python
import secrets
print(secrets.token_hex(32))
```
Add the output as `SECRET_KEY`

### DATABASE_URL
Paste the "Internal Database URL" from Step 2 as `DATABASE_URL`

Example:
```
SECRET_KEY=your-generated-secret-key-here
DATABASE_URL=postgresql://user:password@host/database
```

## Step 5: Deploy

1. Click "Create Web Service"
2. Wait 3-5 minutes for build and deployment
3. Once deployed, click the URL (e.g., `https://ifat-prototype.onrender.com`)

## Step 6: Test Your Deployment

1. Visit your app URL
2. Register as a teacher
3. Create a class and quiz
4. Register as a student (in an incognito window)
5. Join the class and take the quiz

## Troubleshooting

### Build Failed
- Check that `requirements.txt` is in the root directory
- Verify Python version compatibility

### Database Connection Error
- Verify `DATABASE_URL` is correct
- Make sure it starts with `postgresql://` (not `postgres://`)
- The code automatically handles the URL conversion

### App Won't Start
- Check logs in Render dashboard
- Verify `gunicorn app:app` command is correct
- Ensure all dependencies are in `requirements.txt`

### 502 Bad Gateway
- Wait a few minutes - Render free tier can be slow to start
- Check if database is running
- Restart the web service

## Free Tier Limitations

- Database: 1GB storage, 97 hours/month uptime
- Web Service: Spins down after 15 min of inactivity
- First request after spin-down takes 30-60 seconds

## Keeping Your App Alive

For research sessions, you can:
1. Use a service like UptimeRobot to ping your app every 5 minutes
2. Or manually visit the app before your research session

## Backing Up Data

Download CSV exports regularly from the Analytics dashboard to backup your research data.

## Cost Estimate

- **Free Tier**: $0/month (suitable for pilot studies)
- **Paid Tier**: ~$7-25/month (for persistent database and always-on web service)

## Next Steps

After successful deployment:
1. Share the app URL with your research team
2. Create test accounts to verify functionality
3. Set up your classes and quizzes
4. Begin pilot testing with students
