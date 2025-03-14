from flask import Flask, jsonify, request
from datetime import datetime
import sqlite3
import contextlib

app = Flask(__name__)
DATABASE = 'tasks.db'

# Database helper functions
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@contextlib.contextmanager
def db_connection():
    conn = get_db()
    try:
        yield conn
    finally:
        conn.close()

# Initialize database table
with db_connection() as conn:
    conn.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
    ''')
    conn.commit()

# Home Route
@app.route('/')
def home():
    return "Hello, Flask is running on your laptop!"

# CRUD Operations
@app.route('/tasks', methods=['POST'])
def create_task():
    data = request.json
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO tasks (title, description)
            VALUES (?, ?)
        ''', (data['title'], data.get('description')))
        conn.commit()
    return jsonify({'message': 'Task created'}), 201

@app.route('/tasks', methods=['GET'])
def get_tasks():
    status_filter = request.args.get('status')
    search_query = request.args.get('q')
    
    query = 'SELECT * FROM tasks WHERE 1=1'
    params = []
    
    if status_filter:
        query += ' AND status = ?'
        params.append(status_filter)
    if search_query:
        query += ' AND title LIKE ?'
        params.append(f'%{search_query}%')
    
    with db_connection() as conn:
        tasks = conn.execute(query, params).fetchall()
    
    return jsonify([dict(task) for task in tasks])

@app.route('/tasks/<int:id>', methods=['PUT'])
def update_task(id):
    data = request.json
    updates = []
    params = []
    
    if 'title' in data:
        updates.append('title = ?')
        params.append(data['title'])
    if 'description' in data:
        updates.append('description = ?')
        params.append(data['description'])
    if 'status' in data:
        updates.append('status = ?')
        params.append(data['status'])
        if data['status'] == 'completed':
            updates.append('completed_at = ?')
            params.append(datetime.utcnow().isoformat())
    
    params.append(id)
    
    with db_connection() as conn:
        conn.execute(f'''
            UPDATE tasks 
            SET {', '.join(updates)}
            WHERE id = ?
        ''', params)
        conn.commit()
    
    return jsonify({'message': 'Task updated'})

@app.route('/tasks/<int:id>', methods=['DELETE'])
def delete_task(id):
    with db_connection() as conn:
        conn.execute('DELETE FROM tasks WHERE id = ?', (id,))
        conn.commit()
    return jsonify({'message': 'Task deleted'})

# Analytics Endpoint
@app.route('/analytics')
def get_analytics():
    with db_connection() as conn:
        total_tasks = conn.execute('SELECT COUNT(*) FROM tasks').fetchone()[0]
        completed_tasks = conn.execute('SELECT COUNT(*) FROM tasks WHERE status = "completed"').fetchone()[0]
        
        avg_duration = conn.execute('''
            SELECT AVG(
                strftime('%s', completed_at) - strftime('%s', created_at)
            ) 
            FROM tasks 
            WHERE status = 'completed'
        ''').fetchone()[0]
    
    return jsonify({
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'average_completion_seconds': avg_duration
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
