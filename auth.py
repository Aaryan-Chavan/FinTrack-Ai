import jwt
import datetime
from functools import wraps
from flask import request, jsonify, g
from config import Config

def generate_token(user_id):
    """Generates a JWT token valid for 24 hours using timezone-aware UTC."""
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        'exp': now + datetime.timedelta(days=1),
        'iat': now,
        'sub': str(user_id)
    }
    return jwt.encode(payload, Config.SECRET_KEY, algorithm='HS256')

def login_required(f):
    """Decorator to protect routes and extract authenticated user_id from the JWT."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization', '')

        if auth_header.startswith('Bearer '):
            parts = auth_header.split(" ")
            if len(parts) == 2 and parts[1].strip():
                token = parts[1].strip()

        if not token:
            return jsonify({'error': 'Authentication token is missing!'}), 401

        try:
            data = jwt.decode(
                token,
                Config.SECRET_KEY,
                algorithms=['HS256'],
                options={"verify_sub": False}
            )
            sub = data.get('sub')
            if sub is None:
                return jsonify({'error': 'Invalid token payload!'}), 401
            g.user_id = int(sub)
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired! Please log in again.'}), 401
        except (jwt.InvalidTokenError, ValueError, TypeError):
            return jsonify({'error': 'Invalid token!'}), 401

        return f(*args, **kwargs)

    return decorated