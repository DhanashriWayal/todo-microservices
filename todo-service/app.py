from flask import Flask, request, jsonify
from pymongo import MongoClient
from jose import jwt
from bson import ObjectId
import os
import json
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allow all origins (for development)
@app.route('/', endpoint='root_health')
def health():
    return jsonify({"status": "ok", "service": "user-service"}), 200

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGODB_URI)
db = client["tododb"]
todos = db["todos"]

JWT_SECRET = os.getenv("JWT_SECRET", "fallback-secret")
JWT_ALGORITHM = "HS256"

@app.route('/')
def health():
    return jsonify({"status": "healthy", "service": "todo-service"}), 200
def get_user_id():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload['sub']
    except:
        return None

@app.route('/todos', methods=['POST'])
def create_todo():
    user_id = get_user_id()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        data = json.loads(request.data.decode('utf-8')) if request.data else {}
        title = data.get('title', '').strip()
        if not title:
            return jsonify({"error": "Title required"}), 400

        todo = {
            "user_id": ObjectId(user_id),
            "title": title,
            "description": data.get('description', '').strip(),
            "completed": False
        }
        result = todos.insert_one(todo)
        todo['_id'] = str(result.inserted_id)
        todo['user_id'] = str(todo['user_id'])
        return jsonify(todo), 201
    except Exception as e:
        print(f"[ERROR] Create todo: {e}")
        return jsonify({"error": "Failed to create"}), 500

@app.route('/todos', methods=['GET'])
def get_todos():
    user_id = get_user_id()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        cursor = todos.find({"user_id": ObjectId(user_id)})
        out = [{**t, '_id': str(t['_id']), 'user_id': str(t['user_id'])} for t in cursor]
        return jsonify(out)
    except Exception as e:
        print(f"[ERROR] Get todos: {e}")
        return jsonify({"error": "Failed to fetch"}), 500

@app.route('/todos/<todo_id>', methods=['PUT'])
def update_todo(todo_id):
    user_id = get_user_id()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        data = json.loads(request.data.decode('utf-8')) if request.data else {}
        update = {k: v for k, v in data.items() if k in ('title', 'description', 'completed')}
        if 'completed' in update:
            update['completed'] = bool(update['completed'])
        if not update:
            return jsonify({"error": "No fields"}), 400
        result = todos.update_one(
            {"_id": ObjectId(todo_id), "user_id": ObjectId(user_id)},
            {"$set": update}
        )
        return jsonify({"message": "Updated" if result.modified_count else "Not found"}), 200
    except Exception as e:
        print(f"[ERROR] Update: {e}")
        return jsonify({"error": "Update failed"}), 500

@app.route('/todos/<todo_id>', methods=['DELETE'])
def delete_todo(todo_id):
    user_id = get_user_id()
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        result = todos.delete_one({"_id": ObjectId(todo_id), "user_id": ObjectId(user_id)})
        return jsonify({"message": "Deleted" if result.deleted_count else "Not found"}), 200
    except Exception as e:
        print(f"[ERROR] Delete: {e}")
        return jsonify({"error": "Delete failed"}), 500

if __name__ == '__main__':
    port = int(os.getenv("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False)