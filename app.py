import sqlite3
import time
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
DB_NAME = "database.db"


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Users jadvali
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance REAL DEFAULT 0,
            energy INTEGER DEFAULT 1000,
            max_energy INTEGER DEFAULT 1000,
            level INTEGER DEFAULT 1,
            last_sync INTEGER
        )
    """
    )

    # Inventory (Artefaktlar) jadvali
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            item_name TEXT,
            rarity TEXT,
            boost_multiplier REAL
        )
    """
    )

    # Season Pass (Battle Pass) jadvali
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS season_pass (
            level_required INTEGER PRIMARY KEY,
            reward_coins INTEGER,
            description TEXT
        )
    """
    )

    # Claimed Pass jadvali
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS claimed_pass (
            user_id INTEGER,
            pass_level INTEGER,
            PRIMARY KEY (user_id, pass_level)
        )
    """
    )

    # Dastlabki Season Pass mukofotlarini kiritish
    cursor.execute(
        "INSERT OR IGNORE INTO season_pass VALUES (1, 1000, 'Boshlang'ich Mukofot')"
    )
    cursor.execute(
        "INSERT OR IGNORE INTO season_pass VALUES (2, 5000, 'Bronza Jamg'arma')"
    )
    cursor.execute(
        "INSERT OR IGNORE INTO season_pass VALUES (3, 15000, 'Kumush Sandiq')"
    )
    cursor.execute(
        "INSERT OR IGNORE INTO season_pass VALUES (5, 50000, 'Oltin Qalampir')"
    )

    conn.commit()
    conn.close()


init_db()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/sync", methods=["POST"])
def sync():
    data = request.json or {}
    user_id = data.get("user_id", 123456)
    username = data.get("username", "Guest")
    now = int(time.time())

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    if not user:
        cursor.execute(
            "INSERT INTO users (user_id, username, balance, energy, max_energy, level, last_sync) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, username, 0, 1000, 1000, 1, now),
        )
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()

    # Passiv daromad hisoblash (Sekundiga 0.5 coin)
    time_passed = now - user["last_sync"]
    passive_gained = min(time_passed * 0.5, 10000)  # Cheklov 10,000 coin
    new_balance = user["balance"] + passive_gained

    cursor.execute(
        "UPDATE users SET balance = ?, last_sync = ? WHERE user_id = ?",
        (new_balance, now, user_id),
    )
    conn.commit()

    return jsonify(
        {
            "user_id": user["user_id"],
            "balance": new_balance,
            "energy": user["energy"],
            "max_energy": user["max_energy"],
            "level": user["level"],
            "passive_gained": round(passive_gained, 1),
        }
    )


@app.route("/api/tap", methods=["POST"])
def tap():
    data = request.json or {}
    user_id = data.get("user_id")
    taps = data.get("taps", 1)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    if user and user["energy"] >= taps:
        new_balance = user["balance"] + taps
        new_energy = user["energy"] - taps
        # Level oshirish logikasi (Har 1000 coin uchun 1 level)
        new_level = max(1, int(new_balance // 1000) + 1)

        cursor.execute(
            "UPDATE users SET balance = ?, energy = ?, level = ? WHERE user_id = ?",
            (new_balance, new_energy, new_level, user_id),
        )
        conn.commit()
        return jsonify(
            {
                "success": True,
                "balance": new_balance,
                "energy": new_energy,
                "level": new_level,
            }
        )

    return jsonify({"success": False, "reason": "Energikangiz yetarli emas!"})


@app.route("/api/open_lootbox", methods=["POST"])
def open_lootbox():
    data = request.json or {}
    user_id = data.get("user_id")
    cost = 5000

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    if user and user["balance"] >= cost:
        new_balance = user["balance"] - cost
        cursor.execute(
            "UPDATE users SET balance = ? WHERE user_id = ?",
            (new_balance, user_id),
        )

        import random

        rarities = [
            ("Odatdiy Qalampir", "Common", 1.2, 70),
            ("Oltin Qalampir", "Rare", 1.5, 20),
            ("Olovli Qalampir", "Legendary", 2.0, 10),
        ]
        chosen = random.choices(
            rarities, weights=[r[3] for r in rarities], k=1
        )[0]

        cursor.execute(
            "INSERT INTO inventory (user_id, item_name, rarity, boost_multiplier) VALUES (?, ?, ?, ?)",
            (user_id, chosen[0], chosen[1], chosen[2]),
        )
        conn.commit()

        return jsonify(
            {
                "success": True,
                "item": {
                    "name": chosen[0],
                    "rarity": chosen[1],
                    "boost_multiplier": chosen[2],
                },
            }
        )

    return jsonify({"success": False, "reason": "Mablag' yetarli emas!"})


@app.route("/api/pass_info", methods=["POST"])
def pass_info():
    data = request.json or {}
    user_id = data.get("user_id")
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM season_pass")
    passes = [dict(row) for row in cursor.fetchall()]

    cursor.execute(
        "SELECT pass_level FROM claimed_pass WHERE user_id = ?", (user_id,)
    )
    claimed = [row["pass_level"] for row in cursor.fetchall()]

    return jsonify({"passes": passes, "claimed": claimed})


@app.route("/api/user_inventory", methods=["POST"])
def user_inventory():
    data = request.json or {}
    user_id = data.get("user_id")
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM inventory WHERE user_id = ?", (user_id,))
    items = [dict(row) for row in cursor.fetchall()]

    return jsonify({"items": items})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
