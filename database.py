import sqlite3

def setup_database():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS points (
            user_id TEXT PRIMARY KEY,
            score INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def add_points(user_id, points=1):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT score FROM points WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    
    if row:
        new_score = row[0] + points
        cursor.execute('UPDATE points SET score = ? WHERE user_id = ?', (new_score, user_id))
    else:
        cursor.execute('INSERT INTO points (user_id, score) VALUES (?, ?)', (user_id, points))
        
    conn.commit()
    conn.close()

def get_points(user_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT score FROM points WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return row[0]
    else:
        return 0
