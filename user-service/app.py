from flask import Flask, request, jsonify
from pymongo import MongoClient
import bcrypt
from jose import jwt
from bson import ObjectId
import os
import json
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allow all origins (for development)

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGODB_URI)
db = client["userdb"]
users = db["users"]

JWT_SECRET = os.getenv("JWT_SECRET", "fallback-secret")
JWT_ALGORITHM = "HS256"

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        if not all([username, password, email]):
            return jsonify({"error": "All fields required"}), 400
        if users.find_one({"$or": [{"username": username}, {"email": email}]}):
            return jsonify({"error": "User or email exists"}), 400

        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        user = {
            "username": username,
            "email": email,
            "password": hashed,
            "profile": {"bio": "", "location": ""}
        }
        result = users.insert_one(user)
        return jsonify({"message": "User created", "id": str(result.inserted_id)}), 201
    except Exception as e:
        print(f"[ERROR] Register: {e}")
        return jsonify({"error": "Registration failed"}), 500

@app.route('/profile', methods=['GET'])
def get_profile():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user = users.find_one({"_id": ObjectId(payload['sub'])})
        if not user:
            return jsonify({"error": "User not found"}), 404
        return jsonify({
            "username": user["username"],
            "email": user["email"],
            "profile": user["profile"]
        })
    except Exception:
        return jsonify({"error": "Invalid token"}), 401

@app.route('/profile', methods=['PUT'])
def update_profile():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        data = request.get_json() or {}
        update = {
            "profile.bio": data.get("bio", ""),
            "profile.location": data.get("location", "")
        }
        result = users.update_one(
            {"_id": ObjectId(payload['sub'])},
            {"$set": update}
        )
        return jsonify({"message": "Profile updated" if result.modified_count else "No changes"})
    except Exception:
        return jsonify({"error": "Invalid token"}), 401

@app.route('/verify', methods=['POST'])
def verify():
    try:
        data = request.get_json()
        user = users.find_one({"username": data.get('username')})
        if user and bcrypt.checkpw(data.get('password', '').encode('utf-8'), user['password']):
            return jsonify({"id": str(user["_id"]), "username": user["username"]})
        return jsonify({"error": "Invalid credentials"}), 401
    except Exception as e:
        print(f"[ERROR] Verify: {e}")
        return jsonify({"error": "Verification failed"}), 500

if __name__ == '__main__':
    port = int(os.getenv("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False)