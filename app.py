import os
import sqlite3
import time
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'qalampir_crypto_secret_2026'

# Render va WebSocket barqarorligi uchun eventlet bilan integratsiya
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

DB_PATH = os.path.join(os.path.dirname(__file__), 'database.db')
ONLINE_USERS = set()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance REAL DEFAULT 0.0,
            energy INTEGER DEFAULT 1000,
            max_energy INTEGER DEFAULT 1000,
            click_power REAL DEFAULT 0.001,
            recharge_rate INTEGER DEFAULT 1,
            last_sync INTEGER
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/init', methods=['POST'])
def init_user():
    data = request.get_json() or {}
    user_id = data.get('user_id', 123456)
    username = data.get('username', 'Player')
    now = int(time.time())

    conn = get_db()
    cursor = conn.cursor()
    user = cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()

    if not user:
        cursor.execute('''
            INSERT INTO users (user_id, username, balance, energy, max_energy, click_power, recharge_rate, last_sync)
            VALUES (?, ?, 0.0, 1000, 1000, 0.001, 1, ?)
        ''', (user_id, username, now))
        conn.commit()
        user = cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
    else:
        # Offlayn vaqtida energiyani avtomatik tiklash
        elapsed = now - user['last_sync']
        recovered_energy = elapsed * user['recharge_rate']
        new_energy = min(user['max_energy'], user['energy'] + recovered_energy)
        cursor.execute('UPDATE users SET energy = ?, last_sync = ? WHERE user_id = ?', (new_energy, now, user_id))
        conn.commit()
        user = cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()

    conn.close()
    return jsonify(dict(user))

@app.route('/api/sync', methods=['POST'])
def sync_clicks():
    data = request.get_json() or {}
    user_id = data.get('user_id')
    clicks = data.get('clicks', 0)
    now = int(time.time())

    if not user_id:
        return jsonify({'error': 'No user_id provided'}), 400

    conn = get_db()
    cursor = conn.cursor()
    user = cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()

    if user:
        click_power = user['click_power']
        gained_balance = clicks * click_power
        new_balance = round(user['balance'] + gained_balance, 4)
        new_energy = max(0, user['energy'] - clicks)

        cursor.execute('''
            UPDATE users SET balance = ?, energy = ?, last_sync = ? WHERE user_id = ?
        ''', (new_balance, new_energy, now, user_id))
        conn.commit()
        conn.close()
        return jsonify({'balance': new_balance, 'energy': new_energy, 'status': 'ok'})

    conn.close()
    return jsonify({'error': 'User not found'}), 404

# WebSocket real-vaqt rejimida onlayn sonini uzatadi
@socketio.on('connect')
def handle_connect():
    ONLINE_USERS.add(request.sid)
    emit('online_status', {'online_count': len(ONLINE_USERS)}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    ONLINE_USERS.discard(request.sid)
    emit('online_status', {'online_count': len(ONLINE_USERS)}, broadcast=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
