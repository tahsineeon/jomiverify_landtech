# JomiVerify — LandTech Hackathon MVP

**Challenge:** LA-181 · Digital Land Records, Verification & Digitization  
**Type:** Beginner-friendly Flask + SQLite web prototype  
**Data:** Synthetic/fictitious demo records only

## What it demonstrates
- A structured form for digitizing land-record details.
- Search by record ID, owner/applicant, district, upazila, mouza, khatian or dag.
- Duplicate screening for the same district/upazila/mouza/khatian/dag combination.
- A verification code plus SHA-256 fingerprint to check whether the saved demo fields match their stored fingerprint.
- A local audit log for record creation and verification attempts.
- Responsive dashboard and record detail pages.

## Run on macOS
1. Install Python 3 if needed.
2. Open Terminal and move into this folder:
   ```bash
   cd jomiverify_landtech
   ```
3. Create a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Start the app:
   ```bash
   python app.py
   ```
6. Open `http://127.0.0.1:5000` in your browser.

The database file `land_records.db` is created automatically with three fictional sample records on first run.

## Demo flow (2–3 minutes)
1. Open Overview and explain the problem hypothesis.
2. Open Records and search for `Tarash` or `JV-2026-1001`.
3. Open a sample record; show the verification code and SHA-256 fingerprint.
4. Go to Verify, enter the record ID and code, and show all three checks passing.
5. Try a wrong code to show a failed check.
6. Go to Add record and try entering the same mouza/khatian/dag combination as an existing record to demonstrate duplicate screening.
7. Show the audit trail.

## Important limitations
This is a proof-of-concept, not a government service. It does not connect to official Bangladesh land databases, authenticate people, validate deeds, establish legal ownership, or detect fraud in the source document. A hash only detects changes relative to the stored fingerprint; an operator able to edit both the database fields and hash can bypass this simple design. The local audit log is not tamper-proof. Use only synthetic data in the hackathon demo.

## Suggested next steps if time allows
- Add a document scan/photo upload and human review status.
- Add role-based accounts (data-entry operator and reviewer).
- Add Bengali labels and a printable verification summary.
- Integrate only with authorized government data sources after approval.
