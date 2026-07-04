import sqlite3
import psycopg2
import os
from config import DATABASE_URL

DB_PATH = os.path.join(os.path.dirname(__file__), "testbot.db")

def get_connection():
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL)
    return sqlite3.connect(DB_PATH)

def _execute(cursor, query, params=()):
    if DATABASE_URL:
        query = query.replace('?', '%s')
    cursor.execute(query, params)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    if DATABASE_URL:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id SERIAL PRIMARY KEY,
                text TEXT NOT NULL,
                option1 TEXT NOT NULL,
                option2 TEXT NOT NULL,
                option3 TEXT NOT NULL,
                correct_option INTEGER NOT NULL,
                topic TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS results (
                id SERIAL PRIMARY KEY,
                chat_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                username TEXT,
                topic TEXT NOT NULL,
                correct_count INTEGER DEFAULT 0,
                total_count INTEGER DEFAULT 0,
                last_test_date TIMESTAMP,
                UNIQUE(chat_id, user_id, topic)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS active_polls (
                poll_id TEXT PRIMARY KEY,
                chat_id BIGINT NOT NULL,
                question_id INTEGER NOT NULL,
                correct_option INTEGER NOT NULL
            )
        ''')
    else:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                option1 TEXT NOT NULL,
                option2 TEXT NOT NULL,
                option3 TEXT NOT NULL,
                correct_option INTEGER NOT NULL,
                topic TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT,
                topic TEXT NOT NULL,
                correct_count INTEGER DEFAULT 0,
                total_count INTEGER DEFAULT 0,
                last_test_date TIMESTAMP,
                UNIQUE(chat_id, user_id, topic)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS active_polls (
                poll_id TEXT PRIMARY KEY,
                chat_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                correct_option INTEGER NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY
            )
        ''')
        
    conn.commit()
    conn.close()

def add_question(text, opt1, opt2, opt3, correct_idx, topic):
    conn = get_connection()
    cursor = conn.cursor()
    _execute(cursor, '''
        INSERT INTO questions (text, option1, option2, option3, correct_option, topic)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (text, opt1, opt2, opt3, correct_idx, topic))
    conn.commit()
    conn.close()

def get_all_questions():
    conn = get_connection()
    cursor = conn.cursor()
    _execute(cursor, 'SELECT id, text, topic FROM questions ORDER BY id DESC')
    res = cursor.fetchall()
    conn.close()
    return res

def delete_question(q_id):
    conn = get_connection()
    cursor = conn.cursor()
    _execute(cursor, 'DELETE FROM questions WHERE id = ?', (q_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def get_topics():
    conn = get_connection()
    cursor = conn.cursor()
    _execute(cursor, 'SELECT DISTINCT topic FROM questions WHERE topic IS NOT NULL')
    res = [row[0] for row in cursor.fetchall()]
    conn.close()
    return res

def get_questions_by_topic(topic):
    conn = get_connection()
    cursor = conn.cursor()
    _execute(cursor, 'SELECT id, text, option1, option2, option3, correct_option FROM questions WHERE topic = ?', (topic,))
    res = cursor.fetchall()
    conn.close()
    return res

def add_active_poll(poll_id, chat_id, question_id, correct_option):
    conn = get_connection()
    cursor = conn.cursor()
    _execute(cursor, '''
        INSERT INTO active_polls (poll_id, chat_id, question_id, correct_option)
        VALUES (?, ?, ?, ?)
    ''', (poll_id, chat_id, question_id, correct_option))
    conn.commit()
    conn.close()

def get_active_poll(poll_id):
    conn = get_connection()
    cursor = conn.cursor()
    _execute(cursor, 'SELECT chat_id, question_id, correct_option FROM active_polls WHERE poll_id = ?', (poll_id,))
    res = cursor.fetchone()
    conn.close()
    return res

def remove_active_poll(poll_id):
    conn = get_connection()
    cursor = conn.cursor()
    _execute(cursor, 'DELETE FROM active_polls WHERE poll_id = ?', (poll_id,))
    conn.commit()
    conn.close()

def update_user_result(chat_id, user_id, username, topic, is_correct):
    conn = get_connection()
    cursor = conn.cursor()
    
    _execute(cursor, '''
        SELECT correct_count, total_count FROM results
        WHERE chat_id = ? AND user_id = ? AND topic = ?
    ''', (chat_id, user_id, topic))
    row = cursor.fetchone()
    
    if row:
        correct_count = row[0] + (1 if is_correct else 0)
        total_count = row[1] + 1
        
        _execute(cursor, '''
            UPDATE results
            SET correct_count = ?, total_count = ?, username = ?, last_test_date = CURRENT_TIMESTAMP
            WHERE chat_id = ? AND user_id = ? AND topic = ?
        ''', (correct_count, total_count, username, chat_id, user_id, topic))
    else:
        correct_count = 1 if is_correct else 0
        total_count = 1
        _execute(cursor, '''
            INSERT INTO results (chat_id, user_id, username, topic, correct_count, total_count, last_test_date)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (chat_id, user_id, username, topic, correct_count, total_count))
        
    conn.commit()
    conn.close()

def get_user_stats(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    _execute(cursor, '''
        SELECT topic, SUM(correct_count), SUM(total_count)
        FROM results
        WHERE user_id = ?
        GROUP BY topic
    ''', (user_id,))
    res = cursor.fetchall()
    conn.close()
    return res

def get_chat_rating(chat_id, topic=None):
    conn = get_connection()
    cursor = conn.cursor()
    
    if topic:
        _execute(cursor, '''
            SELECT username, correct_count, total_count
            FROM results
            WHERE chat_id = ? AND topic = ?
            ORDER BY correct_count DESC, total_count ASC
            LIMIT 10
        ''', (chat_id, topic))
    else:
        _execute(cursor, '''
            SELECT username, SUM(correct_count) as c, SUM(total_count) as t
            FROM results
            WHERE chat_id = ?
            GROUP BY user_id
            ORDER BY c DESC, t ASC
            LIMIT 10
        ''', (chat_id,))
    
    res = cursor.fetchall()
    conn.close()
    return res

def is_admin(user_id):
    from config import ADMIN_IDS
    if user_id in ADMIN_IDS:
        return True
    conn = get_connection()
    c = conn.cursor()
    _execute(c, "SELECT user_id FROM admins WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return bool(row)

def add_admin(user_id):
    conn = get_connection()
    c = conn.cursor()
    if DATABASE_URL:
        c.execute("INSERT INTO admins (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING", (user_id,))
    else:
        c.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def remove_admin(user_id):
    conn = get_connection()
    c = conn.cursor()
    _execute(c, "DELETE FROM admins WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
