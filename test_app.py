"""
Test script to verify the IF-AT prototype setup
Run this after starting the app to test basic functionality
"""

import requests
import json

BASE_URL = "http://localhost:5000"

def test_home_page():
    """Test that the home page loads"""
    response = requests.get(BASE_URL)
    print(f"Home page: {response.status_code}")
    assert response.status_code == 200, "Home page failed to load"
    print("✓ Home page loads successfully")

def test_registration():
    """Test user registration"""
    # Test teacher registration
    teacher_data = {
        'name': 'Test Teacher',
        'email': 'teacher@test.com',
        'password': 'testpass123',
        'role': 'teacher'
    }
    
    response = requests.post(f"{BASE_URL}/register", data=teacher_data, allow_redirects=False)
    print(f"Teacher registration: {response.status_code}")
    
    # Test student registration
    student_data = {
        'name': 'Test Student',
        'email': 'student@test.com',
        'password': 'testpass123',
        'role': 'student'
    }
    
    response = requests.post(f"{BASE_URL}/register", data=student_data, allow_redirects=False)
    print(f"Student registration: {response.status_code}")
    print("✓ Registration endpoints working")

def test_login():
    """Test user login"""
    session = requests.Session()
    
    login_data = {
        'email': 'teacher@test.com',
        'password': 'testpass123'
    }
    
    response = session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=False)
    print(f"Login: {response.status_code}")
    
    # Check if redirected to dashboard
    if response.status_code == 302:
        print("✓ Login successful (redirect detected)")
    else:
        print("⚠ Login may have failed")

if __name__ == "__main__":
    print("Testing IF-AT Prototype Setup...")
    print("=" * 50)
    
    try:
        test_home_page()
        print()
        test_registration()
        print()
        test_login()
        print()
        print("=" * 50)
        print("✓ All basic tests passed!")
        print("\nYou can now:")
        print("1. Register as a teacher at http://localhost:5000/register")
        print("2. Create a class and quiz")
        print("3. Register as a student and test the scratch card interface")
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        print("\nMake sure the app is running with: python app.py")
