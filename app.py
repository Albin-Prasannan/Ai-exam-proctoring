from time import time
from flask import Flask, request, redirect, render_template, session, flash,jsonify,g
import sqlite3
from proctoring.proctoring_engine import start_proctoring
from proctoring.control import stop_event
from werkzeug.security import generate_password_hash, check_password_hash
import random
import os
from sqlite3 import IntegrityError
import random
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from flask import request, jsonify, session
from proctoring.violation_tracker import log_violation as track_violation
from proctoring.video_proctoring import log_violation as file_violation, clear_violation



port = int(os.environ.get("PORT", 5050))
TOTAL_QUESTIONS = 0
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecret123")
print("APP INSTANCE:", id(app))
print("SECRET KEY:", app.secret_key)
proctoring_running = False

@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


@app.route("/")
def home():
    return render_template("login.html")

# DATABASE CONNECTION
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "database.db")

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(
            db_path,
            timeout=10  # waits if DB is locked
        )
        g.db.row_factory = sqlite3.Row
    return g.db



def send_email(to_email, password):
    try:
        api_key = os.environ.get("SENDGRID_API_KEY")

        if not api_key:
            print("SendGrid key missing")
            return "Email config missing"

        message = Mail(
            from_email='albinprasannan1532@gmail.com',
            to_emails=to_email,
            subject='Your Account Details',
            html_content=f"""
            <h3>Welcome to Online Exam System</h3>
            <p>Email: {to_email}</p>
            <p>Password: {password}</p>
            """
        )

        sg = SendGridAPIClient(api_key)
        sg.send(message)

        return "Email sent"

    except Exception as e:
        print("EMAIL ERROR:", e)
        return "Email failed"
    
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        role = request.form.get("role")

        if not name or not email or not role:
            return "All fields are required"

        default_password = str(random.randint(100000, 999999))
        hashed_password = generate_password_hash(default_password)

        db = get_db()

        
        try:
            for i in range(3):
                try:
                    db.execute("""
                        INSERT INTO users (name, email, password, role)
                        VALUES (?, ?, ?, ?)
                    """, (name, email, hashed_password, role))
                    db.commit()
                    break
                except sqlite3.OperationalError as e:
                    if "locked" in str(e):
                        time.sleep(1)
                    else:
                        raise

        except IntegrityError:
            return "Email already exists"

        try:
            email_status = send_email(email, default_password)
        except Exception as e:
            print("Email crash:", e)
            email_status = "Email failed"

        return "Signup successful! " + email_status

    return render_template("signup.html")

# LOGIN

@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    password = request.form.get("password")

    db = get_db()

    user = db.execute(
        "SELECT * FROM users WHERE email = ?",
        (email,)
    ).fetchone()

    if not user:
        return "Invalid Email ❌"

    if not check_password_hash(user["password"], password):
        return "Invalid Password ❌"

    # ✅ SAFE role handling
    role = user["role"]

    if not role:
        return "Role missing for this user ❌"

    role = role.strip().lower()

    session["user_id"] = user["id"]
    session["role"] = role

    # 🔀 Redirect
    if role == "admin":
        return redirect("/admin")

    elif role == "faculty":
        return redirect("/faculty")

    elif role == "student":
        return redirect(f"/student_dashboard/{user['id']}")

    return "Role not defined ❌"

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ADMIN DASHBOARD
@app.route("/admin")
def admin():
    if "user_id" not in session or session["role"] != "admin":
        return redirect("/")
    return render_template("admin.html")

# ADD USER
@app.route("/add_user", methods=["GET", "POST"])
def add_user():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        role = request.form["role"]
        hashed_password = generate_password_hash(password) 
        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            (name, email, hashed_password, role)
        )
        db.commit()

        return redirect("/view_users")

    return render_template("add_user.html")

# VIEW USERS
@app.route("/view_users")
def view_users():
    db = get_db()
    users = db.execute("SELECT * FROM users").fetchall()
    return render_template("view_users.html", users=users)

# DELETE USER
@app.route("/delete_user/<int:user_id>")
def delete_user(user_id):
    db = get_db()
    db.execute("DELETE FROM users WHERE id=?", (user_id,))
    db.commit()
    return redirect("/view_users")

# EDIT USER
@app.route("/edit_user/<int:user_id>", methods=["GET", "POST"])
def edit_user(user_id):
    db = get_db()

    if request.method == "POST":
        name = request.form["name"]
        role = request.form["role"]

        db.execute(
            "UPDATE users SET name=?, role=? WHERE id=?",
            (name, role, user_id)
        )
        db.commit()

        return redirect("/view_users")

    user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    return render_template("edit_user.html", user=user)

# Add Questions Form Page
@app.route("/add_questions_form")
def add_questions_form():
    db = get_db()
    
    # 🔐 Protect route
    if "user_id" not in session or session["role"] != "faculty":
        return redirect("/")
    
    selected_exam_id = request.args.get('exam_id')
    
    # Get all exams
    exams = db.execute("SELECT * FROM exams").fetchall()
    
    # Calculate count and total for questions added
    count = 0
    total = 0
    if selected_exam_id:
        count = db.execute("SELECT COUNT(*) FROM questions WHERE exam_id = ?", (selected_exam_id,)).fetchone()[0]
        total_row = db.execute("SELECT total_questions FROM exams WHERE id = ?", (selected_exam_id,)).fetchone()
        if total_row:
            total = total_row["total_questions"]
    
    return render_template("add_questions.html", exams=exams, selected_exam_id=selected_exam_id, count=count, total=total)

#Add Question
@app.route("/add_question", methods=["GET", "POST"])
def add_question():
    db = get_db()

    # 🔐 Protect route
    if "user_id" not in session or session["role"] != "faculty":
        return redirect("/")

    if request.method == "POST":
        q = request.form.get("question")
        o1 = request.form.get("o1")
        o2 = request.form.get("o2")
        o3 = request.form.get("o3")
        o4 = request.form.get("o4")
        ans = request.form.get("answer")

        exam_id = int(request.form.get("exam_id"))

        # 🔥 GET LIMIT
        exam = db.execute(
            "SELECT total_questions FROM exams WHERE id = ?",
            (exam_id,)
        ).fetchone()

        if not exam:
            flash("Invalid Exam ID", "error")
            return redirect("/faculty")

        total = exam["total_questions"]

        # 🔥 COUNT EXISTING QUESTIONS
        count = db.execute(
            "SELECT COUNT(*) as count FROM questions WHERE exam_id = ?",
            (exam_id,)
        ).fetchone()["count"]

        # ❌ BLOCK IF LIMIT REACHED
        if count >= total:
            flash(f"Limit reached ({total})", "error")
            return redirect("/faculty")

        # ✅ INSERT QUESTION
        db.execute("""
            INSERT INTO questions 
            (exam_id, question, option1, option2, option3, option4, correct_answer) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (exam_id, q, o1, o2, o3, o4, ans))

        db.commit()

        # 🔥 REDIRECT TO ADD QUESTIONS FORM WITH EXAM PRE-SELECTED
        if count + 1 >= total:
            flash("All questions added for this exam", "success")
            return redirect("/faculty")
        else:
            flash("Question added successfully", "success")
            return redirect(f"/add_questions_form?exam_id={exam_id}")

    # GET request, redirect to add questions form
    return redirect("/add_questions_form")

# EXAM
@app.route("/exam/<int:exam_id>")
def exam(exam_id):
    db = get_db()

    student_id = 1  # later session

    # ✅ Get exam details
    exam = db.execute(
        "SELECT * FROM exams WHERE id = ?",
        (exam_id,)
    ).fetchone()

    if not exam:
        return redirect(f"/student_dashboard/{session.get('user_id', '')}")

    limit = exam["total_questions"]
    duration = exam["duration"]

    # ✅ Validate duration - ensure it's a positive integer
    try:
        duration = int(duration) if duration is not None else 30  # Default to 30 minutes
        if duration <= 0:
            duration = 30  # Default to 30 minutes if invalid
    except (ValueError, TypeError):
        duration = 30  # Default to 30 minutes if conversion fails

    # ✅ Fetch limited questions
    questions = db.execute(
    "SELECT * FROM questions WHERE exam_id = ? ORDER BY RANDOM() LIMIT ?",
    (exam_id, limit)
).fetchall()

    questions = list(questions)
    random.shuffle(questions)

    final_questions = []

    for q in questions:
        options = [
            q["option1"],
            q["option2"],
            q["option3"],
            q["option4"]
        ]

        random.shuffle(options)

        final_questions.append({
            "id": q["id"],
            "question": q["question"],
            "options": options
        })

    global proctoring_running
    if not proctoring_running:
        start_proctoring()
        proctoring_running = True

    return render_template(
        "exam.html",
        questions=final_questions,
        exam_id=exam_id,
        student_id=student_id,
        duration=duration
    )

@app.route('/video')
def video():
    return "Camera stream here"

#Submit Exam
@app.route("/submit_exam", methods=["POST"])
def submit_exam():
    db = get_db()

    # ✅ CHECK LOGIN
    if "user_id" not in session:
        return redirect("/")

    student_id = session["user_id"]
    exam_id = request.form.get("exam_id")

    # ❌ SAFETY CHECK
    if not exam_id:
        return "Invalid Exam Submission"

    # 🔒 PREVENT MULTIPLE ATTEMPTS
    existing = db.execute(
        "SELECT * FROM results WHERE student_id=? AND exam_id=?",
        (student_id, exam_id)
    ).fetchone()

    if existing:
        return redirect(f"/student_dashboard/{student_id}")

    # ✅ GET QUESTIONS ONLY FOR THIS EXAM
    questions = db.execute(
        "SELECT * FROM questions WHERE exam_id=?",
        (exam_id,)
    ).fetchall()

    score = 0
    total = len(questions)

    # ✅ CALCULATE SCORE
    for q in questions:
        selected = request.form.get(f"q{q['id']}")

        if selected and selected == q["correct_answer"]:
            score += 1

    # ✅ SAVE RESULT WITH DATE
    from datetime import datetime
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    db.execute("""
        INSERT INTO results (student_id, exam_id, score, total, date)
        VALUES (?, ?, ?, ?, ?)
    """, (student_id, exam_id, score, total, date))

    db.commit()

    global proctoring_running
    if proctoring_running:
        stop_event.set()
        proctoring_running = False

    # ✅ REDIRECT BACK TO DASHBOARD
    return redirect(f"/student_dashboard/{student_id}")
#admin result view
@app.route("/view_results")
def view_results():
    if "user_id" not in session or session["role"] not in ["faculty", "admin"]:
        return redirect("/")

    db = get_db()

    results = db.execute("""
        SELECT users.name, users.email, exams.subject, results.score, results.total, results.date
        FROM results
        JOIN users ON results.student_id = users.id
        JOIN exams ON results.exam_id = exams.id
    """).fetchall()

    return render_template("view_results.html", results=results)


#change password
@app.route("/change_password", methods=["GET", "POST"])
def change_password():
    if request.method == "POST":
        email = request.form["email"]
        old_pass = request.form["old_password"]
        new_pass = request.form["new_password"]

        db = get_db()

        # 🔍 Get user by email ONLY
        user = db.execute(
            "SELECT * FROM users WHERE email=?",
            (email,)
        ).fetchone()

        if not user:
            return "❌ User not found"

        # ✅ Check old password using hash
        if not check_password_hash(user["password"], old_pass):
            return "❌ Incorrect old password"

        # 🔐 Hash new password
        new_hashed = generate_password_hash(new_pass)

        # ✅ Update password
        db.execute(
            "UPDATE users SET password=? WHERE email=?",
            (new_hashed, email)
        )
        db.commit()

        return "✅ Password changed successfully"

    return render_template("change_password.html")

#set question count 
@app.route("/set_question_limit", methods=["GET", "POST"])
def set_question_limit():
    db = get_db()

    if request.method == "POST":
        subject = request.form.get("subject")
        total = int(request.form.get("total"))
        duration = int(request.form.get("duration"))

        db.execute("""
            INSERT INTO exams (subject, total_questions, duration)
            VALUES (?, ?, ?)
        """, (subject, total, duration))
        exam_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.commit()

        return redirect(f"/add_questions_form?exam_id={exam_id}")

    return render_template("add_questions.html")
      
#student dashboard
@app.route("/student_dashboard/<int:student_id>")
def student_dashboard(student_id):
    db = get_db()

    # 🔐 सुरक्षा (important)
    if "user_id" not in session or session["user_id"] != student_id:
        return redirect("/")

    # 📚 All exams
    exams = db.execute("SELECT * FROM exams").fetchall()

    # 📊 Get full results with exam info
    results = db.execute("""
        SELECT 
            results.exam_id,
            results.score,
            results.total,
            results.date,
            exams.subject
        FROM results
        JOIN exams ON results.exam_id = exams.id
        WHERE results.student_id = ?
    """, (student_id,)).fetchall()

    # 🔄 Convert to dictionary (easy to use in HTML)
    result_dict = {}
    for r in results:
        result_dict[r["exam_id"]] = {
            "score": r["score"],
            "total": r["total"],
            "date": r["date"],
            "subject": r["subject"]
        }

    return render_template(
        "student_dashboard.html",
        exams=exams,
        results=result_dict,
        student_id=student_id
    )
#faculty dashboard
@app.route("/faculty")
def faculty_dashboard():
    if "user_id" not in session or session["role"] != "faculty":
        return redirect("/")

    db = get_db()

    selected_exam_id = request.args.get('exam_id')

    # Get all exams for the add question form
    exams = db.execute("SELECT * FROM exams").fetchall()

    # Calculate count and total for questions added
    if selected_exam_id:
        count = db.execute("SELECT COUNT(*) FROM questions WHERE exam_id = ?", (selected_exam_id,)).fetchone()[0]
        total = db.execute("SELECT total_questions FROM exams WHERE id = ?", (selected_exam_id,)).fetchone()["total_questions"]
    else:
        count = 0
        total = 0

    # Get results for view results section
    results = db.execute("""
        SELECT users.name as student_name, exams.subject as exam_subject, 
               results.score, results.total, results.date,
               (results.score * 100.0 / results.total) as percentage
        FROM results
        JOIN users ON results.student_id = users.id
        JOIN exams ON results.exam_id = exams.id
        ORDER BY results.date DESC
    """).fetchall()

    return render_template("faculty.html", exams=exams, results=results, count=count, total=total, selected_exam_id=selected_exam_id)


@app.route('/report_violation', methods=['POST'])
def report_violation():
    try:
        data = request.get_json()
        status = data.get("status", "").lower()

        if "user_id" not in session:
            return jsonify({"error": "Not logged in"}), 403

        db = get_db()

        # 🧠 classify type
        if "face" in status or "multiple" in status:
            track_violation("face")
        elif "voice" in status or "audio" in status:
            track_violation("audio")
        elif "looking" in status:
            track_violation("eye_tracking")
        else:
            track_violation("eye")

        # 💾 store in DB
        db.execute(
            "INSERT INTO logs (student_id, event) VALUES (?, ?)",
            (session["user_id"], status)
        )
        db.commit()

        # 📝 optional file log (for real-time status)
        file_violation(status)

        return jsonify({"success": True})

    except Exception as e:
        print("Violation error:", e)
        return jsonify({"error": "Failed"}), 500


@app.route('/clear_violation', methods=['POST'])
def clear_violation_route():
    clear_violation()
    return jsonify({"success": True})
# ALWAYS LAST
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port)





















