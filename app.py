from flask import Flask, render_template, request, redirect, url_for, send_file, session
import sqlite3
import os
import pandas as pd
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'

db_path = 'disabled_students.db'
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def init_db():
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            trno TEXT NOT NULL,
            disabled_by TEXT NOT NULL,
            reason TEXT NOT NULL,
            image_path TEXT,
            date_disabled TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def do_login():
    role = request.form['role']
    username = request.form['username']
    session['username'] = username
    session['role'] = role
    if role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif role == 'boss':
        return redirect(url_for('boss_dashboard'))
    else:
        return redirect(url_for('login'))
# logout functionality
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

    student_name = request.form['student_name']
    trno = request.form['trno']
    disabled_by = session['username']
    reason = request.form['reason']
    image = request.files['image']
    image_filename = None

    if image and image.filename:
        image_filename = image.filename
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

    date_disabled = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute(
        "INSERT INTO reports (student_name, trno, disabled_by, reason, image_path, date_disabled) VALUES (?, ?, ?, ?, ?, ?)",
        (student_name, trno, disabled_by, reason, image_filename, date_disabled)
    )
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

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    init_db()
    app.run(debug=True)
