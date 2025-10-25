import os
import jwt
import time
from functools import wraps
from flask import request, jsonify

# Load environment variables
JWT_SECRET = os.getenv("JWT_SECRET", "fallback_secret_change_me_in_production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
TOKEN_EXPIRATION = 3600  # 1 hour in seconds (can be modified as needed)

VALID_USERS = {"admin": "caprae@123", "analyst": "leadgen@456"}


def generate_token(username):
    payload = {"username": username, "exp": time.time() + TOKEN_EXPIRATION}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token):
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return decoded if decoded["exp"] >= time.time() else None
    except Exception as e:
        print(f"Token verification failed: {e}")
        return None


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not token or not token.startswith("Bearer "):
            return jsonify({"error": "Authorization header missing or invalid"}), 401

        verified = verify_token(token.split(" ")[1])
        if not verified:
            return jsonify({"error": "Invalid or expired token"}), 401

        return f(*args, **kwargs)

    return decorated
