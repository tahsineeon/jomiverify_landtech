from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3, hashlib, secrets, os
from datetime import datetime
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "land_records.db"
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-this-key")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def canonical_payload(row):
    fields = ["record_id", "owner_name", "district", "upazila", "mouza", "khatian_no",
              "dag_no", "land_area", "land_unit", "record_type", "notes"]
    return "|".join(str(row[k] or "").strip() for k in fields)

def record_hash(data):
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

def log_action(conn, record_id, action, detail):
    conn.execute(
        "INSERT INTO audit_log (record_id, action, detail, created_at) VALUES (?, ?, ?, ?)",
        (record_id, action, detail, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )

def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS land_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        record_id TEXT UNIQUE NOT NULL,
        owner_name TEXT NOT NULL,
        district TEXT NOT NULL,
        upazila TEXT NOT NULL,
        mouza TEXT NOT NULL,
        khatian_no TEXT NOT NULL,
        dag_no TEXT NOT NULL,
        land_area TEXT NOT NULL,
        land_unit TEXT NOT NULL DEFAULT 'decimal',
        record_type TEXT NOT NULL DEFAULT 'Khatian entry',
        notes TEXT DEFAULT '',
        verification_code TEXT NOT NULL,
        content_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        record_id TEXT NOT NULL,
        action TEXT NOT NULL,
        detail TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)
    count = conn.execute("SELECT COUNT(*) AS n FROM land_records").fetchone()["n"]
    if count == 0:
        samples = [
            dict(record_id="JV-2026-1001", owner_name="Rahim Uddin (Sample)", district="Sirajganj",
                 upazila="Tarash", mouza="Tarash Sadar", khatian_no="S-KH-1042", dag_no="D-88",
                 land_area="12.50", land_unit="decimal", record_type="Khatian entry",
                 notes="Synthetic demo record. Not an official land record."),
            dict(record_id="JV-2026-1002", owner_name="Fatema Begum (Sample)", district="Bogura",
                 upazila="Shibganj", mouza="Shibganj", khatian_no="S-KH-2210", dag_no="D-142",
                 land_area="7.25", land_unit="decimal", record_type="Mutation entry",
                 notes="Synthetic demo record. Not an official land record."),
            dict(record_id="JV-2026-1003", owner_name="Karim Ahmed (Sample)", district="Dhaka",
                 upazila="Savar", mouza="Savar", khatian_no="S-KH-9001", dag_no="D-501",
                 land_area="4.00", land_unit="decimal", record_type="Khatian entry",
                 notes="Synthetic demo record. Not an official land record.")
        ]
        for item in samples:
            item["verification_code"] = secrets.token_hex(3).upper()
            item["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            item["content_hash"] = record_hash("|".join(str(item[k]) for k in [
                "record_id","owner_name","district","upazila","mouza","khatian_no","dag_no",
                "land_area","land_unit","record_type","notes"]))
            conn.execute("""INSERT INTO land_records
                (record_id, owner_name, district, upazila, mouza, khatian_no, dag_no, land_area,
                 land_unit, record_type, notes, verification_code, content_hash, created_at)
                 VALUES (:record_id, :owner_name, :district, :upazila, :mouza, :khatian_no, :dag_no,
                 :land_area, :land_unit, :record_type, :notes, :verification_code, :content_hash, :created_at)""", item)
            log_action(conn, item["record_id"], "SAMPLE_CREATED", "Synthetic sample record added during setup.")
    conn.commit()
    conn.close()

def check_integrity(row):
    return record_hash(canonical_payload(row)) == row["content_hash"]

@app.route("/")
def index():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) n FROM land_records").fetchone()["n"]
    districts = conn.execute("SELECT COUNT(DISTINCT district) n FROM land_records").fetchone()["n"]
    logs = conn.execute("SELECT COUNT(*) n FROM audit_log").fetchone()["n"]
    recent = conn.execute("SELECT * FROM land_records ORDER BY id DESC LIMIT 5").fetchall()
    conn.close()
    return render_template("index.html", total=total, districts=districts, logs=logs, recent=recent)

@app.route("/records")
def records():
    q = request.args.get("q", "").strip()
    conn = get_db()
    if q:
        like = f"%{q}%"
        rows = conn.execute("""SELECT * FROM land_records WHERE
            record_id LIKE ? OR owner_name LIKE ? OR district LIKE ? OR upazila LIKE ?
            OR mouza LIKE ? OR khatian_no LIKE ? OR dag_no LIKE ?
            ORDER BY id DESC""", (like, like, like, like, like, like, like)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM land_records ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("records.html", records=rows, q=q)

@app.route("/records/new", methods=["GET", "POST"])
def new_record():
    if request.method == "POST":
        fields = ["owner_name", "district", "upazila", "mouza", "khatian_no", "dag_no", "land_area"]
        data = {field: request.form.get(field, "").strip() for field in fields}
        data["land_unit"] = request.form.get("land_unit", "decimal").strip()
        data["record_type"] = request.form.get("record_type", "Khatian entry").strip()
        data["notes"] = request.form.get("notes", "").strip()
        if any(not data[f] for f in fields):
            flash("Please fill in all required fields.", "error")
            return render_template("new_record.html", form=request.form)
        conn = get_db()
        conflict = conn.execute("""SELECT record_id FROM land_records
            WHERE district=? AND upazila=? AND mouza=? AND khatian_no=? AND dag_no=? LIMIT 1""",
            (data["district"], data["upazila"], data["mouza"], data["khatian_no"], data["dag_no"])).fetchone()
        if conflict:
            flash(f"Possible duplicate: the same mouza/khatian/dag combination already exists as {conflict['record_id']}. Review before saving.", "error")
            conn.close()
            return render_template("new_record.html", form=request.form)
        data["record_id"] = "JV-" + datetime.now().strftime("%Y") + "-" + secrets.token_hex(3).upper()
        data["verification_code"] = secrets.token_hex(3).upper()
        data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data["content_hash"] = record_hash("|".join(str(data[k]) for k in [
            "record_id","owner_name","district","upazila","mouza","khatian_no","dag_no",
            "land_area","land_unit","record_type","notes"]))
        conn.execute("""INSERT INTO land_records
            (record_id, owner_name, district, upazila, mouza, khatian_no, dag_no, land_area,
             land_unit, record_type, notes, verification_code, content_hash, created_at)
             VALUES (:record_id, :owner_name, :district, :upazila, :mouza, :khatian_no, :dag_no,
             :land_area, :land_unit, :record_type, :notes, :verification_code, :content_hash, :created_at)""", data)
        log_action(conn, data["record_id"], "RECORD_CREATED", "Record entered through the digitization form.")
        conn.commit()
        conn.close()
        flash(f"Record created. Verification code: {data['verification_code']} — save it for the demo.", "success")
        return redirect(url_for("record_detail", record_id=data["record_id"]))
    return render_template("new_record.html", form={})

@app.route("/records/<record_id>")
def record_detail(record_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM land_records WHERE record_id=?", (record_id,)).fetchone()
    if not row:
        conn.close()
        flash("Record not found.", "error")
        return redirect(url_for("records"))
    integrity_ok = check_integrity(row)
    logs = conn.execute("SELECT * FROM audit_log WHERE record_id=? ORDER BY id DESC", (record_id,)).fetchall()
    conn.close()
    return render_template("detail.html", record=row, integrity_ok=integrity_ok, logs=logs)

@app.route("/verify", methods=["GET", "POST"])
def verify():
    result = None
    if request.method == "POST":
        record_id = request.form.get("record_id", "").strip()
        code = request.form.get("verification_code", "").strip().upper()
        conn = get_db()
        row = conn.execute("SELECT * FROM land_records WHERE record_id=?", (record_id,)).fetchone()
        if row:
            integrity_ok = check_integrity(row)
            code_ok = secrets.compare_digest(row["verification_code"], code)
            result = {"record": row, "integrity_ok": integrity_ok, "code_ok": code_ok,
                      "verified": integrity_ok and code_ok}
            log_action(conn, record_id, "VERIFICATION_ATTEMPT",
                       "Successful demo verification." if result["verified"] else "Verification failed or integrity mismatch.")
            conn.commit()
        else:
            result = {"record": None, "integrity_ok": False, "code_ok": False, "verified": False}
        conn.close()
    return render_template("verify.html", result=result)

@app.route("/audit")
def audit():
    conn = get_db()
    logs = conn.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT 100").fetchall()
    conn.close()
    return render_template("audit.html", logs=logs)

@app.route("/about")
def about():
    return render_template("about.html")

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
