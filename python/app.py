from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'ccs_sitin_secret_key'

# Changed to 'database.db' for better compatibility
DATABASE = 'database.db'

# ─────────────────────────────────────────────
# DATABASE SETUP
# ─────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id_number    TEXT PRIMARY KEY,
            last_name    TEXT NOT NULL,
            first_name   TEXT NOT NULL,
            middle_name  TEXT,
            course_level TEXT,
            password     TEXT NOT NULL,
            email        TEXT NOT NULL,
            course       TEXT,
            address      TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@app.route('/')
def home():
    # This renders your login page
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    id_number = request.form.get('id_number')
    password  = request.form.get('password')

    # Admin fallback
    if id_number == "admin" and password == "1234":
        session['user'] = 'admin'
        session['name'] = 'Admin'
        return redirect(url_for('dashboard'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id_number = ? AND password = ?', (id_number, password))
    user = cursor.fetchone()
    conn.close()

    if user:
        session['user'] = user['id_number']
        session['name'] = user['first_name']
        flash('Login successful!', 'success')
        return redirect(url_for('dashboard'))
    else:
        flash('Invalid ID number or password.', 'error')
        return redirect(url_for('home'))

@app.route('/register_page')
def register_page():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register():
    # Getting data from your new form structure
    id_number        = request.form.get('id_number')
    last_name        = request.form.get('last_name')
    first_name       = request.form.get('first_name')
    middle_name      = request.form.get('middle_name')
    email            = request.form.get('email')
    address          = request.form.get('address')
    password         = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    course           = request.form.get('course')
    course_level     = request.form.get('course_level')

    # Validation
    if password != confirm_password:
        flash('Passwords do not match.', 'error')
        return redirect(url_for('register_page'))

    conn = get_db()
    cursor = conn.cursor()

    # Check for existing ID
    cursor.execute('SELECT * FROM users WHERE id_number = ?', (id_number,))
    if cursor.fetchone():
        flash('ID Number already registered.', 'error')
        conn.close()
        return redirect(url_for('register_page'))

    # Save to Database
    try:
        cursor.execute('''
            INSERT INTO users (id_number, last_name, first_name, middle_name, course_level, password, email, course, address)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (id_number, last_name, first_name, middle_name, course_level, password, email, course, address))
        conn.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('home'))
    except Exception as e:
        flash(f'An error occurred: {e}', 'error')
        return redirect(url_for('register_page'))
    finally:
        conn.close()

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('home'))
    return render_template('dashboard.html', name=session.get('name'))

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)