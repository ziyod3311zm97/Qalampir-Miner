import os
import sqlite3
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

# Ma'lumotlar bazasi yo'lini aniqlash
DB_PATH = os.path.join(os.path.dirname(__file__), 'database.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Ma'lumotlar bazasini va jadvallarni yaratish
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Season pass jadvali
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS season_pass (
            id INTEGER PRIMARY KEY,
            points INTEGER,
            reward_name TEXT
        )
    ''')
    
    # Foydalanuvchilar (Users) jadvali
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance INTEGER DEFAULT 0,
            energy INTEGER DEFAULT 1000
        )
    ''')
    
    # Boshlang'ich ma'lumotni xavfsiz (parametrik) usulda kiritish
    cursor.execute(
        "INSERT OR IGNORE INTO season_pass (id, points, reward_name) VALUES (?, ?, ?)",
        (1, 1000, "Boshlang'ich Mukofot")
    )
    
    conn.commit()
    conn.close()

# Server ishga tushishi bilan bazani tayyorlash
init_db()

# Bosh sahifa
@app.route('/')
def home():
    return render_template('index.html') if os.path.exists('templates/index.html') else "Qalampir Miner Serveri Ishlamoqda!"

# Foydalanuvchi ma'lumotlarini olish (API)
@app.route('/api/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
    
    if user is None:
        # Yangi foydalanuvchini ro'yxatdan o'tkazish
        conn.execute('INSERT INTO users (user_id, balance, energy) VALUES (?, ?, ?)', (user_id, 0, 1000))
        conn.commit()
        user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
    
    conn.close()
    return jsonify(dict(user))

# Bosish / Miner (Click) harakatini saqlash (API)
@app.route('/api/click', methods=['POST'])
def click():
    data = request.get_json() or {}
    user_id = data.get('user_id')
    clicks = data.get('clicks', 1)

    if not user_id:
        return jsonify({'error': 'user_id talab qilinadi'}), 400

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()

    if not user:
        conn.close()
        return jsonify({'error': 'Foydalanuvchi topilmadi'}), 404

    new_balance = user['balance'] + clicks
    new_energy = max(0, user['energy'] - clicks)

    conn.execute('UPDATE users SET balance = ?, energy = ? WHERE user_id = ?', 
                 (new_balance, new_energy, user_id))
    conn.commit()
    conn.close()

    return jsonify({'balance': new_balance, 'energy': new_energy})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
