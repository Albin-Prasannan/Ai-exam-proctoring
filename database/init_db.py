import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect("database.db")
c = conn.cursor()

hashed_password = generate_password_hash("admin123")

# ---------------- USERS TABLE ----------------
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL
)
""")

# ---------------- EXAMS TABLE ----------------
c.execute("""
CREATE TABLE IF NOT EXISTS exams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT,
    teacher TEXT,
    total_questions INTEGER,
    duration INTEGER
)
""")

# ---------------- QUESTIONS TABLE ----------------
c.execute("""
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_id INTEGER,
    question TEXT,
    option1 TEXT,
    option2 TEXT,
    option3 TEXT,
    option4 TEXT,
    correct_answer TEXT
)
""")

# ---------------- RESULTS TABLE (🔥 FIXED) ----------------
c.execute("""
CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER,
    exam_id INTEGER,   -- 🔥 IMPORTANT FIX
    score INTEGER,
    total INTEGER,
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# ---------------- LOGS TABLE ----------------
c.execute("""
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER,
    event TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# ---------------- INSERT DEFAULT ADMIN ----------------
c.execute("""
INSERT OR IGNORE INTO users (name, email, password, role)
VALUES (?, ?, ?, ?)
""", ("Admin", "admin@gmail.com", hashed_password, "admin"))

conn.commit()
conn.close()

print("✅ Database created successfully")