
from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime, timedelta, date
import sqlite3
import re
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "mess_secret_key"

# ---------------- UPLOAD ---------------- #
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ---------------- DATABASE ---------------- #
def get_db():
    return sqlite3.connect("database.db")

def init_db():
    con = get_db()
    cur = con.cursor()



    cur.execute("""
    CREATE TABLE IF NOT EXISTS password_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        roll_no TEXT,
        new_password TEXT,
        status TEXT
    )
    """)

    # Users table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        roll_no TEXT,
        password TEXT,
        role TEXT
    )
    """)

    # Feedback table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        roll_no TEXT,
        month TEXT,
        mess_no TEXT,
        q1 TEXT,
        q2 TEXT,
        q3a TEXT,
        q3b TEXT,
        q3c TEXT,
        q4 TEXT,
        q5 TEXT,
        q6 TEXT,
        q7 TEXT,
        q8 TEXT,
        comment TEXT
    )
    """)

    # Remarks table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS remarks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        roll_no TEXT,
        message TEXT,
        image TEXT,
        date TEXT
    )
    """)

    # Absentees table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS absentees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        roll_no TEXT,
        absent_date TEXT,
        meal TEXT
    )
    """)

    # Notifications table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT,
        message TEXT,
        date TEXT
    )
    """)

    con.commit()
    con.close()

# ---------------- ROUTES ---------------- #

@app.route("/")
def home():
    return render_template("login.html")


# ---------- RESET MONTHLY DATA ---------- #
@app.route("/reset_month")
def reset_month():

    if "role" not in session or session["role"] != "admin":
        return redirect("/")

    con = get_db()
    cur = con.cursor()

    cur.execute("DELETE FROM feedback")
    cur.execute("DELETE FROM remarks")
    cur.execute("DELETE FROM absentees")
    cur.execute("DELETE FROM notifications")

    con.commit()
    con.close()

    return redirect("/admin")


# ---------- LOGIN ---------- #
@app.route("/login", methods=["POST"])
def login():
    role = request.form["role"]
    password = request.form["password"]
    if role == "student":
        roll_no = request.form["roll_no"]

        if not re.match(r"^r\d{6}$", roll_no):
            return "Invalid Roll Number Format"

        con = get_db()
        cur = con.cursor()

        cur.execute("SELECT password FROM users WHERE roll_no=?", (roll_no,))
        row = cur.fetchone()

        con.close()

        if row:
            # user already changed password
            if password == row[0]:
                session["roll_no"] = roll_no
                session["role"] = "student"
                return redirect("/student")
            else:
                return "Incorrect Password"
        else:
            # first time login
            if password == roll_no + "@123":
                session["roll_no"] = roll_no
                session["role"] = "student"
                return redirect("/student")
            else:
                return "Incorrect Password"

    elif role == "admin":
        username = request.form["username"]

        if username == "admin" and password == "admin@123":
            session["role"] = "admin"
            return redirect(url_for("admin_dashboard"))
        else:
            return "Invalid Admin Credentials"

    return "Login Failed"

#------Change password -------#
@app.route("/change_password", methods=["GET", "POST"])
def change_password():

    if "role" not in session or session["role"] != "student":
        return redirect("/")

    if request.method == "POST":
        new_password = request.form["new_password"]

        con = get_db()
        cur = con.cursor()

        cur.execute(
            "INSERT INTO password_requests (roll_no, new_password, status) VALUES (?, ?, ?)",
            (session["roll_no"], new_password, "pending")
        )

        con.commit()
        con.close()

        return "Request sent to admin"

    return render_template("change_password.html")



#-------admin view request----#
@app.route("/password_requests")
def password_requests():

    if "role" not in session or session["role"] != "admin":
        return redirect("/")

    con = get_db()
    cur = con.cursor()

    cur.execute("SELECT * FROM password_requests WHERE status='pending'")
    data = cur.fetchall()

    con.close()

    return render_template("password_requests.html", requests=data)



#------Approve password--------#
@app.route("/approve_password/<int:id>")
def approve_password(id):

    if "role" not in session or session["role"] != "admin":
        return redirect("/")

    con = get_db()
    cur = con.cursor()

    cur.execute("SELECT roll_no, new_password FROM password_requests WHERE id=?", (id,))
    row = cur.fetchone()

    if row:
        roll_no, new_password = row

        cur.execute("SELECT * FROM users WHERE roll_no=?", (roll_no,))
        user = cur.fetchone()

        if user:
            cur.execute("UPDATE users SET password=? WHERE roll_no=?", (new_password, roll_no))
        else:
            cur.execute(
                "INSERT INTO users (roll_no, password, role) VALUES (?, ?, ?)",
                (roll_no, new_password, "student")
            )

        cur.execute("UPDATE password_requests SET status='approved' WHERE id=?", (id,))

    con.commit()
    con.close()

    return redirect("/password_requests")



#---------Reject password------------#
@app.route("/reject_password/<int:id>")
def reject_password(id):

    if "role" not in session or session["role"] != "admin":
        return redirect("/")

    con = get_db()
    cur = con.cursor()

    cur.execute("UPDATE password_requests SET status='rejected' WHERE id=?", (id,))

    con.commit()
    con.close()

    return redirect("/password_requests")


# ---------- STUDENT DASHBOARD ---------- #
@app.route("/student")
def student_dashboard():

    if "role" not in session or session["role"] != "student":
        return redirect("/")

    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM notifications ORDER BY id DESC")
    notifications = cur.fetchall()
    con.close()

    return render_template("student_dashboard.html", notifications=notifications)


# ---------- ADMIN DASHBOARD ---------- #
@app.route("/admin")
def admin_dashboard():

    if "role" not in session or session["role"] != "admin":
        return redirect("/")

    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM notifications ORDER BY id DESC")
    notifications = cur.fetchall()
    con.close()

    return render_template("admin_dashboard.html", notifications=notifications)


# ---------- FEEDBACK ---------- #
@app.route("/feedback", methods=["GET", "POST"])
def feedback():

    if "role" not in session:
        return redirect("/")

    if request.method == "POST":

        month = request.form["month"]
        mess_no = request.form["mess_no"]
        q1 = request.form["q1"]
        q2 = request.form["q2"]
        q3a = request.form["q3a"]
        q3b = request.form["q3b"]
        q3c = request.form["q3c"]
        q4 = request.form["q4"]
        q5 = request.form["q5"]
        q6 = request.form["q6"]
        q7 = request.form["q7"]
        q8 = request.form["q8"]
        comment = request.form.get("comment", "")

        con = get_db()
        cur = con.cursor()

        cur.execute(
        """INSERT INTO feedback (
        roll_no, month, mess_no,
        q1, q2, q3a, q3b, q3c,
        q4, q5, q6, q7, q8, comment
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (session["roll_no"], month, mess_no,
        q1, q2, q3a, q3b, q3c,
        q4, q5, q6, q7, q8, comment)
        )

        con.commit()
        con.close()

        return redirect("/student")

    return render_template("feedback.html")


# ---------- REMARKS ---------- #
@app.route("/remarks", methods=["GET", "POST"])
def remarks():

    if "role" not in session:
        return redirect("/")

    if request.method == "POST":

        message = request.form["message"]
        image = request.files.get("image")
        image_filename = None

        if image and image.filename != "":
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            image.save(image_path)
            image_filename = filename

        con = get_db()
        cur = con.cursor()

        cur.execute(
        "INSERT INTO remarks VALUES (NULL, ?, ?, ?, ?)",
        (session["roll_no"], message, image_filename, str(date.today()))
        )

        con.commit()
        con.close()

        return redirect("/student")

    return render_template("remarks.html")


# ---------- ABSENT ---------- #
@app.route("/absent", methods=["GET", "POST"])
def absent():

    if "role" not in session:
        return redirect("/")

    if request.method == "POST":

        absent_date = request.form["date"]
        meal = request.form["meal"]

        con = get_db()
        cur = con.cursor()

        cur.execute(
        "INSERT INTO absentees VALUES (NULL, ?, ?, ?)",
        (session["roll_no"], absent_date, meal)
        )

        con.commit()
        con.close()

        return redirect("/student")

    return render_template("absent.html")


# ---------- VIEW FEEDBACK ---------- #
@app.route("/view_feedback")
def view_feedback():

    if "role" not in session or session["role"] != "admin":
        return redirect("/")

    con = get_db()
    cur = con.cursor()

    cur.execute("SELECT * FROM feedback")
    data = cur.fetchall()

    con.close()

    return render_template("view_feedback.html", feedback=data)


# ---------- VIEW REMARKS ---------- #
@app.route("/view_remarks")
def view_remarks():

    if "role" not in session or session["role"] != "admin":
        return redirect("/")

    con = get_db()
    cur = con.cursor()

    cur.execute("SELECT * FROM remarks")
    remarks = cur.fetchall()

    con.close()

    return render_template("view_remarks.html", remarks=remarks)


# ---------- VIEW ABSENTEES ---------- #
@app.route("/view_absentees")
def view_absentees():

    if "role" not in session or session["role"] != "admin":
        return redirect("/")

    con = get_db()
    cur = con.cursor()

    now = datetime.now()
    today = now.date()
    tomorrow = today + timedelta(days=1)

    current_time = now.time()

    breakfast = datetime.strptime("08:00","%H:%M").time()
    lunch = datetime.strptime("12:00","%H:%M").time()
    dinner = datetime.strptime("19:00","%H:%M").time()

    meals = []

    if current_time < breakfast:
        meals = [(today,"Breakfast"),(today,"Lunch"),(today,"Dinner"),
                 (tomorrow,"Breakfast"),(tomorrow,"Lunch"),(tomorrow,"Dinner")]

    elif current_time < lunch:
        meals = [(today,"Lunch"),(today,"Dinner"),
                 (tomorrow,"Breakfast"),(tomorrow,"Lunch"),(tomorrow,"Dinner")]

    elif current_time < dinner:
        meals = [(today,"Dinner"),
                 (tomorrow,"Breakfast"),(tomorrow,"Lunch"),(tomorrow,"Dinner")]

    else:
        meals = [(tomorrow,"Breakfast"),(tomorrow,"Lunch"),(tomorrow,"Dinner")]

    results = []

    for d,m in meals:
        cur.execute("SELECT COUNT(*) FROM absentees WHERE absent_date=? AND meal=?",(str(d),m))
        count = cur.fetchone()[0]
        results.append((d,m,count))

    con.close()

    return render_template("view_absentees.html", results=results)


# ---------- SEND NOTIFICATION ---------- #
@app.route("/send_notification", methods=["POST"])
def send_notification():

    if "role" not in session:
        return redirect("/")

    message = request.form["message"]

    if session["role"] == "admin":
        sender = "Admin"
    else:
        sender = session["roll_no"]

    con = get_db()
    cur = con.cursor()

    cur.execute(
    "INSERT INTO notifications (sender, message, date) VALUES (?, ?, date('now'))",
    (sender, message)
    )

    con.commit()
    con.close()

    if session["role"] == "admin":
        return redirect("/admin")
    else:
        return redirect("/student")


# ---------- DELETE NOTIFICATION ---------- #
@app.route("/delete_notification/<int:id>")
def delete_notification(id):

    if "role" not in session or session["role"] != "admin":
        return redirect("/")

    con = get_db()
    cur = con.cursor()

    cur.execute("DELETE FROM notifications WHERE id=?", (id,))

    con.commit()
    con.close()

    return redirect("/admin")


# ---------- LOGOUT ---------- #
@app.route("/logout")
def logout():

    session.clear()
    return redirect("/")


# ---------------- RUN ---------------- #
if __name__ == "__main__":

    init_db()
    app.run(debug=True)

