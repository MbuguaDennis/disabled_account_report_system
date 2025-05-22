from flask import Flask, render_template, request, redirect, url_for, send_file, session, jsonify
import sqlite3
import os
import pandas as pd
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'

db_path = 'disabled_students.db'
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --------------------------------------
# Initialize the database
# --------------------------------------
def init_db():
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Create reports table
    c.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            trno TEXT NOT NULL,
            student_class TEXT,
            disabled_by TEXT NOT NULL,
            reason TEXT NOT NULL,
            image_path TEXT,
            date_disabled TEXT NOT NULL
        )
    ''')

    # Create students table
    c.execute('''
        CREATE TABLE IF NOT EXISTS students (
            trno TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            student_class TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

# --------------------------------------
# Load student data from Excel
# --------------------------------------
def load_students_from_excel(path='static/data/students.xlsx'):
    if os.path.exists(path):
        df = pd.read_excel(path)
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        for _, row in df.iterrows():
            c.execute('''
                INSERT OR REPLACE INTO students (trno, name, student_class)
                VALUES (?, ?, ?)
            ''', (str(row['TRNO']), row['Name'], row['Class']))
        conn.commit()
        conn.close()
        print("[INFO] Student data loaded successfully.")
    else:
        print("[WARNING] Excel file not found at", path)

# --------------------------------------
# Routes
# --------------------------------------

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def do_login():
    username = request.form['username']
    role = request.form['role']
    session['username'] = username
    session['role'] = role
    if role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif role == 'boss':
        return redirect(url_for('boss_dashboard'))
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin')
def admin_dashboard():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    return render_template('admin_dashboard.html', username=session['username'])

@app.route('/submit_report', methods=['POST'])
def submit_report():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    trno = request.form['trno'].strip()
    reason = request.form['reason']
    disabled_by = session['username']
    image = request.files.get('image')
    image_filename = None

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT name, student_class FROM students WHERE trno = ?", (trno,))
    student = c.fetchone()
    if not student:
        conn.close()
        return "TRNO not found in student list.", 400

    student_name, student_class = student

    # Save image if provided
    if image and image.filename:
        image_filename = image.filename
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

    date_disabled = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    c.execute('''
        INSERT INTO reports (student_name, trno, student_class, disabled_by, reason, image_path, date_disabled)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (student_name, trno, student_class, disabled_by, reason, image_filename, date_disabled))

    conn.commit()
    conn.close()

    return redirect(url_for('admin_dashboard'))

@app.route('/boss')
def boss_dashboard():
    if 'username' not in session or session['role'] != 'boss':
        return redirect(url_for('login'))

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT * FROM reports ORDER BY date_disabled DESC")
    reports = c.fetchall()
    conn.close()
    return render_template('boss_dashboard.html', reports=reports)

@app.route('/export')
def export():
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM reports", conn)
    excel_path = "disabled_students_report.xlsx"
    df.to_excel(excel_path, index=False)
    conn.close()
    return send_file(excel_path, as_attachment=True)

@app.route('/get_student_info')
def get_student_info():
    trno = request.args.get('trno', '').strip()
    if not trno:
        return jsonify({'error': 'No TRNO provided'}), 400

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT name, student_class FROM students WHERE trno = ?", (trno,))
    result = c.fetchone()
    conn.close()
    if result:
        return jsonify({'name': result[0], 'student_class': result[1]})
    return jsonify({'error': 'Student not found'}), 404

# --------------------------------------
# Main
# --------------------------------------
if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    init_db()
    load_students_from_excel()
    app.run(debug=True)
