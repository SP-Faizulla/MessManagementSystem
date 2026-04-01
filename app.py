from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime, timedelta
import sqlite3
import re
from datetime import date
import os
from werkzeug.utils import secure_filename
from flask import redirect

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

    # Users table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        roll_no TEXT,
        password TEXT,
        role TEXT
    )
    """)

    #feedback
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


    # Remarks table (with image)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS remarks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        roll_no TEXT,
        message TEXT,
        image TEXT,
        date TEXT
    )
    """)

    # Absentees table (date + meal)
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


@app.route("/reset_month")
def reset_month():
    import sqlite3

    conn = sqlite3.connect("mess.db")
    cur = conn.cursor()

    # Delete monthly data
    cur.execute("DELETE FROM feedback")
    cur.execute("DELETE FROM remarks")
    cur.execute("DELETE FROM absentees")
    cur.execute("DELETE FROM notifications")

    conn.commit()
    conn.close()

    return redirect("/admin_dashboard")



# ---------- LOGIN ---------- 
import re

@app.route("/login", methods=["POST"])
def login():
    role = request.form["role"]
    password = request.form["password"]

    if role == "student":
        roll_no = request.form["roll_no"]

        # check roll format rxxxxxx
        if not re.match(r"^r\d{6}$", roll_no):
            return "Invalid Roll Number Format"

        expected_password = roll_no + "@123"

        if password == expected_password:
            session["roll_no"] = roll_no
            session["role"] = "student"
            return redirect(url_for("student_dashboard"))
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
                q1, q2, q3a, q3b, q3c, q4, q5, q6, q7, q8, comment
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (session["roll_no"], month, mess_no, q1, q2, q3a, q3b, q3c, q4, q5, q6, q7, q8, comment)
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

# ---------- ADMIN VIEWS (Updated to render HTML tables) ---------- #
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


from datetime import datetime, timedelta

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
    

# ---------- LOGOUT ---------- #
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


#--------------- Send Notifications route------------------#
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



#----------delete route--------------#

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

# ---------------- RUN ---------------- #
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
