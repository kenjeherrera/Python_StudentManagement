from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'ccs_sitin_secret_key'
DATABASE = 'database.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    # Create Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id_number TEXT PRIMARY KEY,
            last_name TEXT NOT NULL,
            first_name TEXT NOT NULL,
            middle_name TEXT,
            course_level TEXT,
            password TEXT NOT NULL,
            email TEXT NOT NULL,
            course TEXT,
            address TEXT NOT NULL,
            remaining_session INTEGER DEFAULT 30
        )
    ''')
    # Create Sit-in Logs Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sitin_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_number TEXT,
            purpose TEXT,
            lab TEXT,
            login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (id_number) REFERENCES users(id_number)
        )
    ''')
    # Create Announcements Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            date_posted TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        id_number = request.form.get('id_number')
        last_name = request.form.get('last_name')
        first_name = request.form.get('first_name')
        course = request.form.get('course')
        year_level = request.form.get('year_level')
        email = request.form.get('email')
        password = request.form.get('password')
        address = request.form.get('address')

        conn = get_db()
        try:
            conn.execute('''
                INSERT INTO users (id_number, last_name, first_name, course, course_level, email, password, address)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (id_number, last_name, first_name, course, year_level, email, password, address))
            conn.commit()
            flash('Registration successful!', 'success')
            return redirect(url_for('home'))
        except sqlite3.IntegrityError:
            flash('This ID Number is already registered.', 'error')
        finally:
            conn.close()
            
    return render_template('register.html')

@app.route('/login', methods=['POST'])
def login():
    id_number = request.form.get('id_number')
    password = request.form.get('password')

    if id_number == "admin" and password == "1234":
        session.update({'user': 'admin', 'name': 'Admin', 'role': 'admin'})
        return redirect(url_for('dashboard'))

    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id_number = ? AND password = ?', (id_number, password)).fetchone()
    conn.close()

    if user:
        session.update({'user': user['id_number'], 'name': user['first_name'], 'role': 'student'})
        return redirect(url_for('dashboard'))
    
    flash('Invalid ID or password.', 'error')
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('home'))

    conn = get_db()
    row = conn.execute('SELECT content FROM announcements ORDER BY id DESC LIMIT 1').fetchone()
    current_announcement = row['content'] if row else "No new announcements."
    
    registered = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    total_sitin = conn.execute('SELECT COUNT(*) FROM sitin_logs').fetchone()[0]
    conn.close()
    
    return render_template('dashboard.html', 
                           name=session.get('name'), 
                           registered=registered, 
                           sitin=total_sitin,
                           announcement=current_announcement)

@app.route('/sit_in_page')
def sit_in_page():
    if session.get('role') != 'admin':
        return redirect(url_for('dashboard'))
    
    conn = get_db()
    students_data = conn.execute('SELECT * FROM users').fetchall()
    conn.close()
    return render_template('sit_in.html', sitin_records=students_data)

@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if session.get('role') != 'admin':
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        # Collect data from the "Add Student" form
        id_num = request.form.get('id_number')
        last = request.form.get('last_name')
        first = request.form.get('first_name')
        course = request.form.get('course')
        year = request.form.get('year_level')
        pw = request.form.get('password') # Correctly using the Temporary Password
        
        conn = get_db()
        try:
            conn.execute('''
                INSERT INTO users (id_number, last_name, first_name, course, course_level, password, email, address)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (id_num, last, first, course, year, pw, f"{id_num}@sample.com", "N/A"))
            conn.commit()
            flash('Student added successfully!', 'success')
        except Exception as e:
            flash(f'Error: {e}', 'error')
        finally:
            conn.close()
        return redirect(url_for('sit_in_page'))

    return render_template('add_student.html')

@app.route('/process_sitin', methods=['POST'])
def process_sitin():
    if session.get('role') != 'admin':
        return redirect(url_for('dashboard'))

    # Retrieve data from the modal form fields
    id_number = request.form.get('id_number')
    purpose = request.form.get('purpose')
    lab_number = request.form.get('lab_number')
    
    conn = get_db()
    try:
        # 1. Log the session
        conn.execute('INSERT INTO sitin_logs (id_number, purpose, lab) VALUES (?, ?, ?)', 
                     (id_number, purpose, lab_number))
        
        # 2. Subtract 1 from Remaining Session
        conn.execute('UPDATE users SET remaining_session = remaining_session - 1 WHERE id_number = ?', 
                     (id_number,))
        
        conn.commit()
        flash('Sit-in session started!', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'error')
    finally:
        conn.close()

    return redirect(url_for('sit_in_page'))

@app.route('/delete_student/<id_number>') 
def delete_student(id_number):
    if session.get('role') != 'admin':
        return redirect(url_for('dashboard'))
        
    conn = get_db()
    conn.execute('DELETE FROM users WHERE id_number = ?', (id_number,))
    conn.commit()
    conn.close()
    flash('Student deleted successfully', 'success')
    return redirect(url_for('sit_in_page'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# RUN THE APP AT THE VERY END
if __name__ == '__main__':
    init_db()
    app.run(debug=True)