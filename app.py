import sqlite3

def init_db():
    conn = sqlite3.connect('database.db')  # Ma'lumotlar bazasi faylingiz nomi
    cursor = conn.cursor()
    
    # Jadval mavjud bo'lmasa yaratish
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS season_pass (
            id INTEGER PRIMARY KEY,
            points INTEGER,
            reward_name TEXT
        )
    ''')
    
    # Xavfsiz va xatosiz ma'lumot qo'shish (Parametrlardan foydalanilgan)
    cursor.execute(
        "INSERT OR IGNORE INTO season_pass (id, points, reward_name) VALUES (?, ?, ?)",
        (1, 1000, "Boshlang'ich Mukofot")
    )
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
