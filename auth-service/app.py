from flask import Flask, request, jsonify
import requests
from jose import jwt
from datetime import datetime, timedelta
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allow all origins (for development)
@app.route('/')
def health():
    return jsonify({"status": "ok", "service": "user-service"}), 200
JWT_SECRET = os.getenv("JWT_SECRET", "fallback-secret")
JWT_ALGORITHM = "HS256"
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:3001")

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({"error": "Username and password required"}), 400

        resp = requests.post(f"{USER_SERVICE_URL}/verify", json=data, timeout=10)
        if resp.status_code != 200:
            return jsonify({"error": "Invalid credentials"}), 401

        user_data = resp.json()
        token = jwt.encode(
            {
                'sub': user_data['id'],
                'username': user_data['username'],
                'exp': datetime.utcnow() + timedelta(hours=1)
            },
            JWT_SECRET,
            algorithm=JWT_ALGORITHM
        )
        return jsonify({"token": token})
    except Exception as e:
        print(f"[ERROR] Login failed: {e}")
        return jsonify({"error": "Service error"}), 500

if __name__ == '__main__':
    port = int(os.getenv("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False)