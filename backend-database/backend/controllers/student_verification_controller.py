import re
from models.user_model import User, db
from flask import current_app
import os

# List of student/school domains loaded from file
STUDENT_DOMAINS = []
domain_file_path = os.path.join(os.path.dirname(__file__), '..', 'domain_list.txt')
domain_file_path = os.path.abspath(domain_file_path)
print(f"[Student Domain Loader] Loading student domains from {domain_file_path}.")

try:
    with open(domain_file_path, 'r', encoding='utf-8') as f:
        STUDENT_DOMAINS = [line.strip() for line in f if line.strip()]
    print(f"[Student Domain Loader] Loaded {len(STUDENT_DOMAINS)} student domains from {domain_file_path}.")
except UnicodeDecodeError as e:
    print(f"[Student Domain Loader] ⚠️ Unicode decoding failed for {domain_file_path}: {e}")
    STUDENT_DOMAINS = []
except Exception as e:
    print(f"[Student Domain Loader] Error loading student domains from {domain_file_path}: {e}")
    STUDENT_DOMAINS = []

def is_student_email(email):
    """
    Check if the email belongs to a student domain.
    """
    email = email.lower()
    for domain in STUDENT_DOMAINS:
        if email.endswith(domain):
            current_app.logger.info(f"{email} is a student email.")
            return True
    return False

def set_user_as_student(user):
    """
    Set the user's role to 'student' if not already set.
    """
    if user.role != 'student':
        current_app.logger.info(f"Setting user {user.email} role to 'student' after domain and email verification.")
        user.role = 'student'
        db.session.commit()
        return True
    return False