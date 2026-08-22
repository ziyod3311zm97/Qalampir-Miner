import datetime
import random
import sqlite3
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
DB_NAME = "qalampir_miner.db"


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # 1. Foydalanuvchilar jadvali
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        balance REAL DEFAULT 0,
        energy INTEGER DEFAULT 1000,
        max_energy INTEGER DEFAULT 1000,
        exp INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1,
        tap_power REAL DEFAULT 1,
        auto_miner_level INTEGER DEFAULT 0,
        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    )

    # 2. Battle Pass (Sezon bosqichlari)
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS season_pass (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        level_required INTEGER UNIQUE,
        reward_type TEXT, -- 'coins', 'energy', 'artefact'
        reward_value REAL,
        description TEXT
    )
    """
    )

    # Battle Pass uchun boshlang'ich 20 ta daraja mukofotlarini kiritish
    cursor.execute("SELECT COUNT(*) FROM season_pass")
    if cursor.fetchone()[0] == 0:
        for lvl in range(1, 21):
            r_type = "coins" if lvl % 2 != 0 else "energy"
            val = lvl * 500 if r_type == "coins" else lvl * 100
            cursor.execute(
                "INSERT INTO season_pass (level_required, reward_type, reward_value, description) VALUES (?, ?, ?, ?)",
                (lvl, r_type, val, f"{lvl}-Daraja Mukofoti"),
            )

    # 3. Foydalanuvchining da'vo qilgan Battle Pass mukofotlari
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS claimed_pass (
        user_id INTEGER,
        pass_level INTEGER,
        PRIMARY KEY (user_id, pass_level)
    )
    """
    )

    # 4. Inventar (Artefaktlar va Qalampir turlari)
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        item_name TEXT,
        rarity TEXT, -- 'Nodir', 'Afsonaviy', 'Mifik'
        boost_multiplier REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    )

    # 5. Topsiriqlar (Tasks)
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        reward REAL,
        link TEXT
    )
    """
    )

    # Boshlang'ich topsiriqlarni yuklash
    cursor.execute("SELECT COUNT(*) FROM tasks")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO tasks (title, reward, link) VALUES (?, ?, ?)",
            (
                "Telegram kanalga a'zo bo'ling",
                1000,
                "https://t.me/qalampirminerbot",
            ),
        )
        cursor.execute(
            "INSERT INTO tasks (title, reward, link) VALUES (?, ?, ?)",
            ("Do'stni taklif qiling", 2500, ""),
        )

    # 6. Foydalanuvchi bajargan topsiriqlar
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS completed_tasks (
        user_id INTEGER,
        task_id INTEGER,
        PRIMARY KEY (user_id, task_id)
    )
    """
    )

    conn.commit()
    conn.close()


init_db()


# API Endpointlar


@app.route("/api/sync", methods=["POST"])
def sync_user():
    """Foydalanuvchi ma'lumotlarini yuklash va Passiv daromadni (Auto-mining) hisoblash"""
    data = request.json
    user_id = data.get("user_id")
    username = data.get("username", "Miner")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    if not user:
        cursor.execute(
            "INSERT INTO users (user_id, username) VALUES (?, ?)",
            (user_id, username),
        )
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()

    # Passiv daromad hisob-kitobi (agar Auto-miner darajasi > 0 bo'lsa)
    last_act = datetime.datetime.strptime(
        user["last_active"], "%Y-%m-%d %H:%M:%S"
    )
    now = datetime.datetime.now()
    seconds_passed = (now - last_act).total_seconds()

    passive_mined = 0
    if user["auto_miner_level"] > 0 and seconds_passed > 10:
        # Har 1 minutda auto_miner_level * 10 tanga beriladi (maksimum 3 soatgacha)
        minutes = min(seconds_passed // 60, 180)
        passive_mined = minutes * (user["auto_miner_level"] * 10)

    new_balance = user["balance"] + passive_mined
    cursor.execute(
        "UPDATE users SET balance = ?, last_active = ? WHERE user_id = ?",
        (new_balance, now.strftime("%Y-%m-%d %H:%M:%S"), user_id),
    )
    conn.commit()

    return jsonify(
        {
            "user_id": user_id,
            "balance": new_balance,
            "energy": user["energy"],
            "max_energy": user["max_energy"],
            "level": user["level"],
            "exp": user["exp"],
            "tap_power": user["tap_power"],
            "auto_miner_level": user["auto_miner_level"],
            "passive_gained": passive_mined,
        }
    )


@app.route("/api/tap", methods=["POST"])
def tap():
    """Qalampir bosilganda balans va energiyani yangilash"""
    data = request.json
    user_id = data.get("user_id")
    taps_count = data.get("taps", 1)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    if not user or user["energy"] < taps_count:
        return jsonify({"success": False, "reason": "Energiya yetarli emas"}), 400

    earned = taps_count * user["tap_power"]
    new_balance = user["balance"] + earned
    new_energy = user["energy"] - taps_count
    new_exp = user["exp"] + taps_count

    # Daraja oshirish logikasi (har 500 EXPda +1 daraja)
    new_level = user["level"]
    if new_exp >= new_level * 500:
        new_level += 1

    cursor.execute(
        "UPDATE users SET balance = ?, energy = ?, exp = ?, level = ? WHERE user_id = ?",
        (new_balance, new_energy, new_exp, new_level, user_id),
    )
    conn.commit()

    return jsonify(
        {
            "success": True,
            "balance": new_balance,
            "energy": new_energy,
            "exp": new_exp,
            "level": new_level,
        }
    )


@app.route("/api/open_lootbox", methods=["POST"])
def open_lootbox():
    """Gacha / Lootbox tizimi: Qutidan tasodifiy artefakt chiqarish"""
    data = request.json
    user_id = data.get("user_id")
    price = 5000  # Quti narxi

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    if not user or user["balance"] < price:
        return (
            jsonify({"success": False, "reason": "Mablag' yetarli emas"}),
            400,
        )

    # Balansdan ayirish
    cursor.execute(
        "UPDATE users SET balance = balance - ? WHERE user_id = ?",
        (price, user_id),
    )

    # Tasodifiy Artefakt tanlash
    items = [
        {"name": "Olovli Qalampir", "rarity": "Nodir", "multiplier": 1.5},
        {"name": "Oltin Qalampir", "rarity": "Afsonaviy", "multiplier": 3.0},
        {"name": "Kvant Qalampiri", "rarity": "Mifik", "multiplier": 5.0},
    ]
    won = random.choices(items, weights=[70, 25, 5], k=1)[0]

    cursor.execute(
        "INSERT INTO inventory (user_id, item_name, rarity, boost_multiplier) VALUES (?, ?, ?, ?)",
        (user_id, won["name"], won["rarity"], won["multiplier"]),
    )
    conn.commit()

    return jsonify({"success": True, "item": won})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
