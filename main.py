import email
from datetime import datetime, timedelta
import pyodbc
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, Response, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import io
import os
from flask import jsonify
import requests
from smtp_module import send_email_notification
# ✅ Comment out direct SMTP use
# import smtplib
# from email.mime.text import MIMEText
# main.py

from db_module import get_db_connection  # ✅ Import the DB logic from external module



app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this

@app.route('/send_notification', methods=['POST'])
def send_notification():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    student_email = data.get('student_email')
    student_name = data.get('student_name')
    book_name = data.get('book_name')
    issue_date = data.get('issue_date')
    return_date = data.get('return_date')

    if not all([student_email, student_name, book_name, issue_date, return_date]):
        return jsonify({'error': 'Missing required fields'}), 400

    subject = "Library Book Return Reminder - Student"
    body = f"""
    Dear {student_name},

    This is a reminder to return the book "{book_name}" issued on {issue_date}.
    Please return it by {return_date} to avoid any penalties.

    Regards,
    Library Management
    """

    success, message = send_email_notification(student_email, subject, body)

    if success:
        return jsonify({'message': 'Notification sent successfully'}), 200
    else:
        return jsonify({'error': message}), 500


@app.route('/send_staff_notification', methods=['POST'])
def send_staff_notification():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    staff_email = data.get('staff_email')
    staff_name = data.get('staff_name')
    book_name = data.get('book_name')
    issue_date = data.get('issue_date')
    return_date = data.get('return_date')

    subject = "Library Book Return Reminder - Staff"
    body = f"""
    Dear {staff_name},

    This is a reminder to return the book "{book_name}" issued on {issue_date}.
    Please return it by {return_date} to avoid any penalties.

    Regards,
    Library Management
    """

    success, message = send_email_notification(staff_email, subject, body)

    if success:
        return jsonify({'message': 'Notification sent successfully'}), 200
    else:
        return jsonify({'error': message}), 500

@app.route('/')
def home():
    if 'username' in session:
        return render_template('index.html', username=session['username'])
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        if conn is None:
            flash('Database connection failed.', 'error')
            return render_template('login.html')

        cursor = conn.cursor()
        cursor.execute("SELECT username, password_hash FROM Users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[1], password):  # user[1] is password_hash
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirmPassword']

        if password != confirm_password:
            return render_template('Create.html', error='Passwords do not match')

        conn = get_db_connection()
        if conn is None:
            return render_template('Create.html', error='Database connection failed')
        cursor = conn.cursor()

        # Check if username exists
        cursor.execute("SELECT username FROM Users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            return render_template('Create.html', error='Username already exists')

        password_hash = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO Users (name, email, username, password_hash) VALUES (?, ?, ?, ?)",
            (name, email, username, password_hash)
        )
        conn.commit()
        conn.close()

        return redirect(url_for('login'))

    return render_template('Create.html')


@app.route('/new_student', methods=['GET', 'POST'])
def new_student():
    if request.method == 'POST':
        student_id = request.form['student_id']
        name = request.form['name']
        batch = request.form['batch']
        course = request.form['course']
        dob = request.form['dob']
        gender = request.form['gender']
        email = request.form['email']  # Add this line
        phone = request.form['phone']

        if not all([student_id, name, batch, course, dob, gender, email, phone]):  # Add email to validation
            flash('All fields are required.', 'error')
            return redirect(url_for('new_student'))

        try:
            dob = datetime.strptime(dob, '%Y-%m-%d').date().strftime('%Y-%m-%d')
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'error')
            return redirect(url_for('new_student'))

        conn = get_db_connection()
        if conn is None:
            flash('Database connection failed.', 'error')
            return redirect(url_for('new_student'))

        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO Students (student_id, name, batch, course, dob, gender, email, phone) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (student_id, name, batch, course, dob, gender, email, phone))  # Add email to insert
            conn.commit()
            flash('Student registered successfully!', 'success')
        except pyodbc.Error as e:
            flash(f'Error registering student: {e}', 'error')
        finally:
            conn.close()

        return redirect(url_for('new_student'))

    return render_template('Student.html')


@app.route('/new_book', methods=['GET', 'POST'])
def new_book():
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash('Database connection failed.', 'error')
        return render_template('new_book.html')

    cursor = conn.cursor()

    if request.method == 'POST':
        book_id = request.form['book_id']
        book_name = request.form['book_name']
        author_name = request.form['author_name']
        publisher = request.form['publisher']
        edition = request.form.get('edition', '')  # Optional field, default to empty string
        publishing_year = request.form.get('publishing_year', None)  # Optional, default to None
        purchase_date = request.form.get('purchase_date', None)  # Optional, default to None

        # Validate required fields
        if not book_id or not book_name or not author_name:
            flash('Book ID, Book Name, and Author Name are required.', 'error')
            return render_template('new_book.html')

        # Validate optional fields if provided
        if publishing_year and not publishing_year.isdigit():
            flash('Publishing Year must be a valid number.', 'error')
            return render_template('new_book.html')
        if purchase_date:
            try:
                datetime.strptime(purchase_date, '%Y-%m-%d')  # Ensure valid date format
            except ValueError:
                flash('Purchase Date must be in YYYY-MM-DD format.', 'error')
                return render_template('new_book.html')

        try:
            # Check if book_id already exists
            cursor.execute("SELECT book_id FROM Books WHERE book_id = ?", (book_id,))
            if cursor.fetchone():
                flash('Book ID already exists.', 'error')
            else:
                # Insert new book with all fields
                cursor.execute("""
                    INSERT INTO Books (book_id, book_name, author_name, publisher, edition, publishing_year, purchase_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (book_id, book_name, author_name, publisher, edition,
                      int(publishing_year) if publishing_year else None, purchase_date))
                conn.commit()
                flash('Book added successfully!', 'success')
        except pyodbc.Error as e:
            flash(f'Error adding book: {e}', 'error')

    conn.close()
    return render_template('new_book.html')


@app.route('/new_staff', methods=['GET', 'POST'])
def new_staff():
    if request.method == 'POST':
        staff_register = request.form['staff_register']
        staff_name = request.form['staff_name']
        designation = request.form['designation']
        department = request.form['department']
        course = request.form['course']
        date_of_birth = request.form['date_of_birth']
        gender = request.form['gender']
        email = request.form['email']
        phone_number = request.form['phone_number']

        if not all([staff_register, staff_name, designation, department, course, date_of_birth, gender, email, phone_number]):
            flash('All fields are required.', 'error')
            return redirect(url_for('new_staff'))

        try:
            date_of_birth = datetime.strptime(date_of_birth, '%Y-%m-%d').date().strftime('%Y-%m-%d')
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'error')
            return redirect(url_for('new_staff'))

        conn = get_db_connection()
        if conn is None:
            flash('Database connection failed.', 'error')
            return redirect(url_for('new_staff'))

        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO Staff (staff_register, staff_name, designation, department, course, date_of_birth, gender, email, phone_number)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (staff_register, staff_name, designation, department, course, date_of_birth, gender, email, phone_number))
            conn.commit()
            flash('Staff registered successfully!', 'success')
        except pyodbc.Error as e:
            flash(f'Error registering staff: {e}', 'error')
        finally:
            conn.close()

        return redirect(url_for('new_staff'))

    return render_template('new_staff.html')


@app.route('/new_user')
def new_user():
    return "New User Page (Under Construction)"


@app.route('/staff_issue_book', methods=['GET', 'POST'])
def staff_issue_book():
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash('Database connection failed.', 'error')
        return render_template('staff_issue_book.html')

    cursor = conn.cursor()

    # Fetch available books (not issued to students or staff yet)
    cursor.execute("""
        SELECT book_id, book_name, author_name, publisher
        FROM Books 
        WHERE book_id NOT IN (
            SELECT book_id FROM IssuedBooks WHERE return_date IS NULL
            UNION
            SELECT book_id FROM Staff_IssuedBooks WHERE return_date IS NULL
        )
    """)
    books = cursor.fetchall()

    if request.method == 'POST':
        book_id = request.form['book_id']
        staff_register = request.form['staff_register']
        issue_date = datetime.now().strftime('%Y-%m-%d')

        # Fetch staff details including email
        cursor.execute("""
            SELECT staff_name, designation, phone_number, email
            FROM Staff 
            WHERE staff_register = ?
        """, (staff_register,))
        staff = cursor.fetchone()

        if not staff:
            flash('Staff not found.', 'error')
        else:
            try:
                # Insert into Staff_IssuedBooks table
                cursor.execute("""
                    INSERT INTO Staff_IssuedBooks (book_id, staff_register, issue_date) 
                    VALUES (?, ?, ?)
                """, (book_id, staff_register, issue_date))
                conn.commit()

                # Extract staff details
                staff_name = staff[0]
                staff_email = staff[3]  # Email is at index 3
                book_name = next((book[1] for book in books if book[0] == book_id), "Unknown Book")
                return_date = (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d')  # 14-day return period

                # Send email using smtp_module
                subject = "Library Book Issued - Return Reminder (Staff)"
                body = f"""
                Dear {staff_name},

                The book "{book_name}" has been issued to you on {issue_date}.
                Please return it by {return_date} to avoid any penalties.

                Regards,
                Library Management
                """

                success, message = send_email_notification(staff_email, subject, body)
                if success:
                    flash(f'Book issued successfully to {staff_name}! Notification sent to {staff_email}.', 'success')
                else:
                    flash(f'Book issued to {staff_name}, but notification failed: {message}', 'error')

            except pyodbc.Error as e:
                flash(f'Error issuing book: {e}', 'error')

    conn.close()
    return render_template('staff_issue_book.html', books=books, today=datetime.now().strftime('%Y-%m-%d'))



@app.route('/get_staff', methods=['GET'])
def get_staff():
    staff_register = request.args.get('staff_register')
    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'Database connection failed'})

    cursor = conn.cursor()
    cursor.execute("SELECT staff_name, designation, phone_number, email FROM Staff WHERE staff_register = ?",
                   (staff_register,))
    staff = cursor.fetchone()
    conn.close()

    if staff:
        return jsonify({
            'staff_name': staff[0],
            'designation': staff[1],
            'phone_number': staff[2],
            'staff_email': staff[3]  # Added staff_email
        })
    return jsonify({'error': 'Staff not found'})


@app.route('/staff_return_book', methods=['GET', 'POST'])
def staff_return_book():
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash('Database connection failed.', 'error')
        return render_template('staff_return_book.html')

    cursor = conn.cursor()

    if request.method == 'POST':
        issue_id = request.form['issue_id']
        action = request.form.get('action')  # 'return' or 'renew'
        current_date = datetime.now().date()
        current_date_str = current_date.strftime('%Y-%m-%d')  # Convert to string

        # Fetch issue details including new fields
        cursor.execute("""
            SELECT staff_register, book_id, issue_date, renew_count, due_date, fine_amount
            FROM Staff_IssuedBooks 
            WHERE issue_id = ? AND return_date IS NULL
        """, (issue_id,))
        issue = cursor.fetchone()

        if not issue:
            flash('Book already returned or invalid Issue ID.', 'error')
        else:
            staff_register, book_id, issue_date, renew_count, due_date, fine_amount = issue
            issue_date = datetime.strptime(issue_date, '%Y-%m-%d').date()
            # Handle None for renew_count and fine_amount
            renew_count = renew_count if renew_count is not None else 0
            fine_amount = fine_amount if fine_amount is not None else 0.0

            # Calculate due date if not set (default: 7 days + 1 day grace)
            if due_date is None:
                default_return_date = issue_date + timedelta(days=7)
                due_date = default_return_date + timedelta(days=1)
                due_date_str = due_date.strftime('%Y-%m-%d')
                cursor.execute("UPDATE Staff_IssuedBooks SET due_date = ? WHERE issue_id = ?", (due_date_str, issue_id))
                conn.commit()
            else:
                due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
                due_date_str = due_date.strftime('%Y-%m-%d')

            # Calculate fine if overdue
            if current_date > due_date:
                days_overdue = (current_date - due_date).days
                fine_amount = days_overdue * 10.00  # ₹10 per day
                cursor.execute("UPDATE Staff_IssuedBooks SET fine_amount = ? WHERE issue_id = ?", (float(fine_amount), issue_id))
                conn.commit()

            if action == 'return':
                try:
                    # Insert into Staff_Return_book table with new fields
                    cursor.execute("""
                        INSERT INTO Staff_Return_book (issue_id, staff_register, book_id, issue_date, return_date, renew_count, due_date, fine_amount)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (issue_id, staff_register, book_id, issue_date.strftime('%Y-%m-%d'), current_date_str,
                          renew_count, due_date_str, float(fine_amount)))

                    # Update Staff_IssuedBooks to mark as returned
                    cursor.execute("""
                        UPDATE Staff_IssuedBooks 
                        SET return_date = ? 
                        WHERE issue_id = ?
                    """, (current_date_str, issue_id))

                    conn.commit()
                    flash(f'Book returned successfully! Fine: ₹{fine_amount:.2f}', 'success')
                except pyodbc.Error as e:
                    flash(f'Error processing return: {e}', 'error')

            elif action == 'renew':
                if renew_count >= 2:
                    flash('Renewal limit (2) reached. Please return the book.', 'error')
                else:
                    # Extend due date by 7 days per renewal
                    new_return_date = issue_date + timedelta(days=7 * (renew_count + 1))
                    new_due_date = new_return_date + timedelta(days=1)
                    new_due_date_str = new_due_date.strftime('%Y-%m-%d')
                    try:
                        cursor.execute("""
                            UPDATE Staff_IssuedBooks 
                            SET renew_count = renew_count + 1, 
                                due_date = ?,
                                fine_amount = 0.00  -- Reset fine on renewal
                            WHERE issue_id = ?
                        """, (new_due_date_str, issue_id))
                        conn.commit()
                        flash(f'Book renewed successfully! New due date: {new_due_date}', 'success')
                    except pyodbc.Error as e:
                        flash(f'Error renewing book: {e}', 'error')

    # Fetch all issued books that haven't been returned, including new fields and email
    cursor.execute("""
        SELECT sib.issue_id, sib.staff_register, sib.book_id, sib.issue_date, s.staff_name, b.book_name, s.email,
               CASE WHEN sib.due_date IS NOT NULL THEN sib.due_date 
                    ELSE DATEADD(day, 8, sib.issue_date) END AS due_date,
               ISNULL(sib.renew_count, 0) AS renew_count,
               ISNULL(sib.fine_amount, 0.00) AS fine_amount
        FROM Staff_IssuedBooks sib
        JOIN Staff s ON sib.staff_register = s.staff_register
        JOIN Books b ON sib.book_id = b.book_id
        WHERE sib.return_date IS NULL
    """)
    issued_books_raw = cursor.fetchall()
    conn.close()

    # Process issued_books to include default return date (issue_date + 7 days)
    issued_books = []
    for book in issued_books_raw:
        issue_date = datetime.strptime(book[3], '%Y-%m-%d')  # Convert string to datetime
        default_return_date = (issue_date + timedelta(days=7)).strftime('%Y-%m-%d')  # Add 7 days
        issued_books.append(list(book[:7]) + [default_return_date] + list(book[7:]))

    return render_template('staff_return_book.html', issued_books=issued_books, today=datetime.now().strftime('%Y-%m-%d'))

from smtp_module import send_email_notification  # ✅ Make sure this is imported at the top

@app.route('/issue_book', methods=['GET', 'POST'])
def issue_book():
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash('Database connection failed.', 'error')
        return render_template('issue_book.html')

    cursor = conn.cursor()

    # Fetch available books
    cursor.execute("""
        SELECT book_id, book_name, author_name, publisher
        FROM Books 
        WHERE book_id NOT IN (SELECT book_id FROM IssuedBooks WHERE return_date IS NULL)
    """)
    books = cursor.fetchall()

    if request.method == 'POST':
        book_id = request.form['book_id']
        student_roll = request.form['student_roll']
        issue_date = datetime.now().strftime('%Y-%m-%d')

        # Fetch student details including email
        cursor.execute("""
            SELECT name, course, batch, phone, email 
            FROM Students 
            WHERE student_id = ?
        """, (student_roll,))
        student = cursor.fetchone()

        if not student:
            flash('Student not found.', 'error')
        else:
            try:
                # Insert into IssuedBooks table
                cursor.execute("""
                    INSERT INTO IssuedBooks (book_id, student_id, issue_date) 
                    VALUES (?, ?, ?)
                """, (book_id, student_roll, issue_date))
                conn.commit()

                # Extract student details
                student_name = student[0]
                student_email = student[4]
                book_name = next((book[1] for book in books if book[0] == book_id), "Unknown Book")
                return_date = (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d')

                # ✅ Use smtp_module to send the email
                subject = "Library Book Issued - Return Reminder"
                body = f"""
                Dear {student_name},

                The book "{book_name}" has been issued to you on {issue_date}.
                Please return it by {return_date} to avoid any penalties.

                Regards,
                Library Management
                """

                success, message = send_email_notification(student_email, subject, body)
                if success:
                    flash(f'Book issued successfully to {student_name}! Notification sent.', 'success')
                else:
                    flash(f'Book issued to {student_name}, but notification failed: {message}', 'error')

            except pyodbc.Error as e:
                flash(f'Error issuing book: {e}', 'error')

    conn.close()
    return render_template('issue_book.html', books=books, today=datetime.now().strftime('%Y-%m-%d'))


@app.route('/get_student')
def get_student():
    roll = request.args.get('roll')
    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'Database connection failed'})

    cursor = conn.cursor()
    cursor.execute("""
        SELECT name, course, batch, phone, email 
        FROM Students 
        WHERE student_id = ?
    """, (roll,))
    student = cursor.fetchone()
    conn.close()

    if student:
        return jsonify({
            'name': student[0],
            'course': student[1],
            'batch': student[2],
            'phone': student[3],
            'email': student[4]  # Add email to the response
        })
    else:
        return jsonify({'error': 'Student not found'})


@app.route('/return_book', methods=['GET', 'POST'])
def return_book():
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash('Database connection failed.', 'error')
        return render_template('return_book.html')

    cursor = conn.cursor()

    if request.method == 'POST':
        issue_id = request.form['issue_id']
        action = request.form.get('action')  # 'return' or 'renew'
        current_date = datetime.now().date()
        current_date_str = current_date.strftime('%Y-%m-%d')  # Convert to string

        # Fetch issue details including new fields
        cursor.execute("""
            SELECT student_id, book_id, issue_date, renew_count, due_date, fine_amount
            FROM IssuedBooks 
            WHERE issue_id = ? AND return_date IS NULL
        """, (issue_id,))
        issue = cursor.fetchone()

        if not issue:
            flash('Book already returned or invalid Issue ID.', 'error')
        else:
            student_id, book_id, issue_date, renew_count, due_date, fine_amount = issue
            issue_date = datetime.strptime(issue_date, '%Y-%m-%d').date()
            # Handle None for renew_count, default to 0
            renew_count = renew_count if renew_count is not None else 0
            # Handle None for fine_amount, default to 0.0
            fine_amount = fine_amount if fine_amount is not None else 0.0

            # Calculate due date if not set (default: 7 days + 1 day grace)
            if due_date is None:
                default_return_date = issue_date + timedelta(days=7)
                due_date = default_return_date + timedelta(days=1)
                due_date_str = due_date.strftime('%Y-%m-%d')  # Convert to string
                cursor.execute("UPDATE IssuedBooks SET due_date = ? WHERE issue_id = ?", (due_date_str, issue_id))
                conn.commit()
            else:
                due_date = datetime.strptime(due_date, '%Y-%m-%d').date()  # Convert fetched due_date to date object
                due_date_str = due_date.strftime('%Y-%m-%d')  # Ensure string format for later use

            # Calculate fine if overdue
            if current_date > due_date:
                days_overdue = (current_date - due_date).days
                fine_amount = days_overdue * 10.00  # ₹10 per day as float
                cursor.execute("UPDATE IssuedBooks SET fine_amount = ? WHERE issue_id = ?", (float(fine_amount), issue_id))
                conn.commit()

            if action == 'return':
                try:
                    # Insert into Return_book table with new fields
                    cursor.execute("""
                        INSERT INTO Return_book (issue_id, student_id, book_id, issue_date, return_date, renew_count, due_date, fine_amount)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (issue_id, student_id, book_id, issue_date.strftime('%Y-%m-%d'), current_date_str,
                          renew_count, due_date_str, float(fine_amount)))

                    # Update IssuedBooks to mark as returned
                    cursor.execute("""
                        UPDATE IssuedBooks 
                        SET return_date = ? 
                        WHERE issue_id = ?
                    """, (current_date_str, issue_id))

                    conn.commit()
                    flash(f'Book returned successfully! Fine: ₹{fine_amount:.2f}', 'success')
                except pyodbc.Error as e:
                    flash(f'Error processing return: {e}', 'error')

            elif action == 'renew':
                if renew_count >= 2:
                    flash('Renewal limit (2) reached. Please return the book.', 'error')
                else:
                    # Extend due date by 7 days per renewal (total period increases)
                    new_return_date = issue_date + timedelta(days=7 * (renew_count + 1))
                    new_due_date = new_return_date + timedelta(days=1)
                    new_due_date_str = new_due_date.strftime('%Y-%m-%d')  # Convert to string
                    try:
                        cursor.execute("""
                            UPDATE IssuedBooks 
                            SET renew_count = renew_count + 1, 
                                due_date = ?,
                                fine_amount = 0.00  -- Reset fine on renewal
                            WHERE issue_id = ?
                        """, (new_due_date_str, issue_id))
                        conn.commit()
                        flash(f'Book renewed successfully! New due date: {new_due_date}', 'success')
                    except pyodbc.Error as e:
                        flash(f'Error renewing book: {e}', 'error')

    # Fetch all issued books that haven't been returned, including new fields and email
    cursor.execute("""
        SELECT ib.issue_id, ib.student_id, ib.book_id, ib.issue_date, s.name, b.book_name, s.email,
               CASE WHEN ib.due_date IS NOT NULL THEN ib.due_date 
                    ELSE DATEADD(day, 8, ib.issue_date) END AS due_date,
               ISNULL(ib.renew_count, 0) AS renew_count,  -- Use ISNULL to handle NULL as 0
               ISNULL(ib.fine_amount, 0.00) AS fine_amount  -- Use ISNULL to handle NULL as 0.00
        FROM IssuedBooks ib
        JOIN Students s ON ib.student_id = s.student_id
        JOIN Books b ON ib.book_id = b.book_id
        WHERE ib.return_date IS NULL
    """)
    issued_books_raw = cursor.fetchall()
    conn.close()

    # Process issued_books to include default return date (issue_date + 7 days)
    issued_books = []
    for book in issued_books_raw:
        issue_date = datetime.strptime(book[3], '%Y-%m-%d')  # Convert string to datetime
        default_return_date = (issue_date + timedelta(days=7)).strftime('%Y-%m-%d')  # Add 7 days
        issued_books.append(list(book[:7]) + [default_return_date] + list(book[7:]))

    return render_template('return_book.html', issued_books=issued_books, today=datetime.now().strftime('%Y-%m-%d'))

@app.route('/edit_book', methods=['GET', 'POST'])
def edit_book():
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash('Database connection failed.', 'error')
        return render_template('edit_book.html')

    cursor = conn.cursor()

    if request.method == 'POST':
        action = request.form.get('action')
        book_id = request.form.get('book_id')

        if action == 'delete':
            try:
                # Check if the book is currently issued
                cursor.execute("""
                    SELECT book_id FROM IssuedBooks WHERE book_id = ? AND return_date IS NULL
                    UNION
                    SELECT book_id FROM Staff_IssuedBooks WHERE book_id = ? AND return_date IS NULL
                """, (book_id, book_id))
                if cursor.fetchone():
                    flash('Cannot delete book: it is currently issued.', 'error')
                else:
                    cursor.execute("DELETE FROM Books WHERE book_id = ?", (book_id,))
                    conn.commit()
                    flash('Book deleted successfully!', 'success')
            except pyodbc.Error as e:
                flash(f'Error deleting book: {e}', 'error')

        elif action == 'edit':
            book_name = request.form['book_name']
            author_name = request.form['author_name']
            publisher = request.form['publisher']
            edition = request.form.get('edition', '')  # Optional field
            publishing_year = request.form.get('publishing_year', None)  # Optional field
            purchase_date = request.form.get('purchase_date', None)  # Optional field

            # Validate optional fields if provided
            if publishing_year and not publishing_year.isdigit():
                flash('Publishing Year must be a valid number.', 'error')
                return render_template('edit_book.html')
            if purchase_date:
                try:
                    datetime.strptime(purchase_date, '%Y-%m-%d')  # Ensure valid date format
                except ValueError:
                    flash('Purchase Date must be in YYYY-MM-DD format.', 'error')
                    return render_template('edit_book.html')

            try:
                cursor.execute("""
                    UPDATE Books 
                    SET book_name = ?, author_name = ?, publisher = ?, edition = ?, publishing_year = ?, purchase_date = ?
                    WHERE book_id = ?
                """, (book_name, author_name, publisher, edition,
                      int(publishing_year) if publishing_year else None, purchase_date, book_id))
                conn.commit()
                flash('Book updated successfully!', 'success')
            except pyodbc.Error as e:
                flash(f'Error updating book: {e}', 'error')

    # Fetch all books with the new fields for display
    cursor.execute("""
        SELECT book_id, book_name, author_name, publisher, edition, publishing_year, purchase_date 
        FROM Books
    """)
    books = cursor.fetchall()
    conn.close()

    return render_template('edit_book.html', books=books)


@app.route('/edit_staff', methods=['GET', 'POST'])
def edit_staff():
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash('Database connection failed.', 'error')
        return render_template('edit_staff.html')

    cursor = conn.cursor()

    if request.method == 'POST':
        action = request.form.get('action')
        staff_register = request.form.get('staff_register')

        if action == 'delete':
            try:
                cursor.execute("""
                    SELECT staff_register 
                    FROM Staff_IssuedBooks 
                    WHERE staff_register = ?
                """, (staff_register,))
                if cursor.fetchone():
                    flash('Cannot delete staff: they have issued book records.', 'error')
                else:
                    cursor.execute("DELETE FROM Staff WHERE staff_register = ?", (staff_register,))
                    conn.commit()
                    flash('Staff deleted successfully!', 'success')
            except pyodbc.Error as e:
                flash(f'Error deleting staff: {e}', 'error')

        elif action == 'edit':
            staff_name = request.form['staff_name']
            designation = request.form['designation']
            department = request.form['department']
            course = request.form['course']
            date_of_birth = request.form['date_of_birth']
            gender = request.form['gender']
            email = request.form['email']
            phone_number = request.form['phone_number']

            try:
                date_of_birth = datetime.strptime(date_of_birth, '%Y-%m-%d').date().strftime('%Y-%m-%d')
                cursor.execute("""
                    UPDATE Staff 
                    SET staff_name = ?, designation = ?, department = ?, course = ?, date_of_birth = ?, gender = ?, email = ?, phone_number = ?
                    WHERE staff_register = ?
                """, (staff_name, designation, department, course, date_of_birth, gender, email, phone_number, staff_register))
                conn.commit()
                flash('Staff updated successfully!', 'success')
            except ValueError:
                flash('Invalid date format. Please use YYYY-MM-DD.', 'error')
            except pyodbc.Error as e:
                flash(f'Error updating staff: {e}', 'error')

    # Fetch all staff with department and course
    cursor.execute("SELECT staff_register, staff_name, designation, department, course, date_of_birth, gender, email, phone_number FROM Staff")
    staff = cursor.fetchall()
    conn.close()

    return render_template('edit_staff.html', staff=staff)


@app.route('/edit_student', methods=['GET', 'POST'])
def edit_student():
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash('Database connection failed.', 'error')
        return render_template('edit_student.html')

    cursor = conn.cursor()

    if request.method == 'POST':
        action = request.form.get('action')
        student_id = request.form.get('student_id')

        if action == 'delete':
            try:
                cursor.execute("""
                    SELECT student_id 
                    FROM IssuedBooks 
                    WHERE student_id = ?
                """, (student_id,))
                if cursor.fetchone():
                    flash('Cannot delete student: they have issued book records.', 'error')
                else:
                    cursor.execute("DELETE FROM Students WHERE student_id = ?", (student_id,))
                    conn.commit()
                    flash('Student deleted successfully!', 'success')
            except pyodbc.Error as e:
                flash(f'Error deleting student: {e}', 'error')

        elif action == 'edit':
            name = request.form['name']
            batch = request.form['batch']
            course = request.form['course']
            dob = request.form['dob']
            gender = request.form['gender']
            email = request.form['email']  # Add email
            phone = request.form['phone']

            try:
                dob = datetime.strptime(dob, '%Y-%m-%d').date().strftime('%Y-%m-%d')
                cursor.execute("""
                    UPDATE Students 
                    SET name = ?, batch = ?, course = ?, dob = ?, gender = ?, email = ?, phone = ?
                    WHERE student_id = ?
                """, (name, batch, course, dob, gender, email, phone, student_id))  # Add email to update
                conn.commit()
                flash('Student updated successfully!', 'success')
            except ValueError:
                flash('Invalid date format. Please use YYYY-MM-DD.', 'error')
            except pyodbc.Error as e:
                flash(f'Error updating student: {e}', 'error')

    # Fetch all students with email
    cursor.execute("SELECT student_id, name, batch, course, dob, gender, email, phone FROM Students")
    students = cursor.fetchall()
    conn.close()

    return render_template('edit_student.html', students=students)


@app.route('/view_details', methods=['GET', 'POST'])
def view_details():
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash('Database connection failed.', 'error')
        return render_template('view_details.html', report_type='student_details')

    cursor = conn.cursor()

    # Get the selected report type from GET or POST request
    report_type = request.args.get('report_type', 'student_details') if request.method == 'GET' else request.form.get('report_type', 'student_details')

    # Fetch data based on selected report type
    data = {
        'students': [],
        'student_issued': [],
        'student_returned': [],
        'staff': [],
        'staff_issued': [],
        'staff_returned': []
    }

    if report_type == 'student_details':
        cursor.execute("SELECT student_id, name, batch, course, gender, email FROM Students")
        data['students'] = cursor.fetchall()

    elif report_type == 'student_issued':
        cursor.execute("""
            SELECT ib.issue_id, ib.student_id, ib.book_id, ib.issue_date, ib.return_date, ib.due_date, ib.renew_count, ib.fine_amount,
                   s.name, b.book_name, b.edition, b.publishing_year, b.purchase_date
            FROM IssuedBooks ib
            JOIN Students s ON ib.student_id = s.student_id
            JOIN Books b ON ib.book_id = b.book_id
        """)
        data['student_issued'] = cursor.fetchall()

    elif report_type == 'student_returned':
        cursor.execute("""
            SELECT rb.return_id, rb.issue_id, rb.student_id, rb.book_id, rb.issue_date, rb.return_date, rb.due_date, rb.renew_count, rb.fine_amount,
                   s.name, b.book_name, b.edition, b.publishing_year, b.purchase_date
            FROM Return_book rb
            JOIN Students s ON rb.student_id = s.student_id
            JOIN Books b ON rb.book_id = b.book_id
        """)
        data['student_returned'] = cursor.fetchall()

    elif report_type == 'staff_details':
        cursor.execute("SELECT staff_register, staff_name, designation, department, course, gender, email FROM Staff")
        data['staff'] = cursor.fetchall()

    elif report_type == 'staff_issued':
        cursor.execute("""
            SELECT sib.issue_id, sib.staff_register, sib.book_id, sib.issue_date, sib.return_date, sib.due_date, sib.renew_count, sib.fine_amount,
                   s.staff_name, b.book_name, b.edition, b.publishing_year, b.purchase_date
            FROM Staff_IssuedBooks sib
            JOIN Staff s ON sib.staff_register = s.staff_register
            JOIN Books b ON sib.book_id = b.book_id
        """)
        data['staff_issued'] = cursor.fetchall()

    elif report_type == 'staff_returned':
        cursor.execute("""
            SELECT srb.return_id, srb.issue_id, srb.staff_register, srb.book_id, srb.issue_date, srb.return_date, srb.due_date, srb.renew_count, srb.fine_amount,
                   s.staff_name, b.book_name, b.edition, b.publishing_year, b.purchase_date
            FROM Staff_Return_book srb
            JOIN Staff s ON srb.staff_register = s.staff_register
            JOIN Books b ON srb.book_id = b.book_id
        """)
        data['staff_returned'] = cursor.fetchall()

    conn.close()

    # Handle PDF download for the selected report
    if request.method == 'POST' and request.form.get('action') == 'download':
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=1*inch, bottomMargin=1*inch)
        elements = []
        styles = getSampleStyleSheet()

        # Custom styles
        header_style = ParagraphStyle(
            'Header',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#6F2DA8'),
            alignment=1,  # Center
            spaceAfter=10
        )
        subheader_style = ParagraphStyle(
            'SubHeader',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#5A1E86'),
            spaceBefore=20,
            spaceAfter=10
        )
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.grey,
            alignment=1  # Center
        )

        # Add Logo
        logo_path = os.path.join(app.static_folder, 'Logo.jpg')
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=8*inch, height=2*inch)
            logo.hAlign = 'CENTER'
            elements.append(logo)
            elements.append(Spacer(1, 0.2*inch))

        # Header
        elements.append(Paragraph("Library Management System Report", header_style))
        elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))

        # Report content based on report_type
        if report_type == 'student_details':
            elements.append(Paragraph("Student Details", subheader_style))
            headers = ['Student ID', 'Name', 'Batch', 'Course', 'Gender', 'Email']
            table_data = [headers] + [[str(col) if col is not None else 'N/A' for col in row] for row in data['students']]
            table = Table(table_data)

        elif report_type == 'student_issued':
            elements.append(Paragraph("Student Issued Books", subheader_style))
            headers = ['Issue ID', 'Student ID', 'Book ID', 'Issue Date', 'Return Date', 'Due Date', 'Renew Count', 'Fine (₹)',
                       'Student Name', 'Book Name', 'Edition', 'Publishing Year', 'Purchase Date']
            table_data = [headers] + [[str(col) if col is not None else 'Not Returned' if i == 4 else 'N/A' for i, col in enumerate(row)] for row in data['student_issued']]
            table = Table(table_data)

        elif report_type == 'student_returned':
            elements.append(Paragraph("Student Returned Books", subheader_style))
            headers = ['Return ID', 'Issue ID', 'Student ID', 'Book ID', 'Issue Date', 'Return Date', 'Due Date', 'Renew Count', 'Fine (₹)',
                       'Student Name', 'Book Name', 'Edition', 'Publishing Year', 'Purchase Date']
            table_data = [headers] + [[str(col) if col is not None else 'N/A' for col in row] for row in data['student_returned']]
            table = Table(table_data)

        elif report_type == 'staff_details':
            elements.append(Paragraph("Staff Details", subheader_style))
            headers = ['Staff Register', 'Name', 'Designation', 'Department', 'Course', 'Gender', 'Email']
            table_data = [headers] + [[str(col) if col is not None else 'N/A' for col in row] for row in data['staff']]
            table = Table(table_data)

        elif report_type == 'staff_issued':
            elements.append(Paragraph("Staff Issued Books", subheader_style))
            headers = ['Issue ID', 'Staff Register', 'Book ID', 'Issue Date', 'Return Date', 'Due Date', 'Renew Count', 'Fine (₹)',
                       'Staff Name', 'Book Name', 'Edition', 'Publishing Year', 'Purchase Date']
            table_data = [headers] + [[str(col) if col is not None else 'Not Returned' if i == 4 else 'N/A' for i, col in enumerate(row)] for row in data['staff_issued']]
            table = Table(table_data)

        elif report_type == 'staff_returned':
            elements.append(Paragraph("Staff Returned Books", subheader_style))
            headers = ['Return ID', 'Issue ID', 'Staff Register', 'Book ID', 'Issue Date', 'Return Date', 'Due Date', 'Renew Count', 'Fine (₹)',
                       'Staff Name', 'Book Name', 'Edition', 'Publishing Year', 'Purchase Date']
            table_data = [headers] + [[str(col) if col is not None else 'N/A' for col in row] for row in data['staff_returned']]
            table = Table(table_data)

        # Enhanced Table Styling
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6F2DA8')),  # Header background
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),  # Header text color
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('FONTSIZE', (0, 0), (-1, 0), 12),  # Header font size
            ('FONTSIZE', (0, 1), (-1, -1), 10),  # Body font size
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F4F4F4')),  # Light gray background for rows
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#F4F4F4'), colors.white]),  # Alternating row colors
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#5A1E86')),  # Border around table
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.grey),  # Inner grid lines
        ]))
        elements.append(table)

        # Footer (added at the bottom of each page via build method)
        def add_footer(canvas, doc):
            canvas.saveState()
            canvas.setFont('Helvetica', 10)
            canvas.setFillColor(colors.grey)
            footer_text = f"Page {doc.page} - Library Management System © {datetime.now().year}"
            canvas.drawCentredString(letter[0] / 2, 0.5 * inch, footer_text)
            canvas.restoreState()

        # Build the PDF with footer
        doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name=f"{report_type}_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf", mimetype='application/pdf')

    # Render the template with the selected report data
    return render_template('view_details.html', report_type=report_type, **data)

@app.route('/delete_book/<book_id>', methods=['POST'])
def delete_book(book_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    if not conn:
        flash('Database connection failed', 'error')
        return redirect(url_for('edit_book'))

    cursor = conn.cursor()
    try:
        # Check if book is in IssuedBooks
        cursor.execute("""
            SELECT COUNT(*) 
            FROM IssuedBooks 
            WHERE book_id = ? AND return_date IS NULL
        """, (book_id,))
        active_issues = cursor.fetchone()[0]

        if active_issues > 0:
            flash('Cannot delete: Book is currently issued to students', 'error')
        else:
            # Delete from IssuedBooks (returned books history)
            cursor.execute("DELETE FROM IssuedBooks WHERE book_id = ?", (book_id,))
            # Delete from Books
            cursor.execute("DELETE FROM Books WHERE book_id = ?", (book_id,))
            conn.commit()
            flash('Book deleted successfully!', 'success')
    except pyodbc.Error as e:
        flash(f'Error deleting book: {e}', 'error')
    finally:
        conn.close()
    return redirect(url_for('edit_book'))

if __name__ == '__main__':
    app.run(debug=True)