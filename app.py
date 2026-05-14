# ═══════════════════════════════════
#   SCHOOL MANAGEMENT SYSTEM
#   Created By Abdifatah Said
# ═══════════════════════════════════

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'school_system_secret_key_2026'

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

SPREADSHEET_ID = '1dRrx8QUq8XpBiP8TzPb85ObL95LgkDQZI6M72NBbGag'

SUBJECTS = [
    'Math', 'English', 'Science', 'Social Studies',
    'Islamic Studies', 'Somali', 'Computer', 'History',
    'Geography', 'Art', 'Physical Education'
]

# ── GOOGLE SHEETS ──
def get_sheet(sheet_name):
    try:
        if os.environ.get('GOOGLE_PRIVATE_KEY'):
            creds_info = {
                "type": os.environ.get('GOOGLE_TYPE', 'service_account'),
                "project_id": os.environ.get('GOOGLE_PROJECT_ID'),
                "private_key_id": os.environ.get('GOOGLE_PRIVATE_KEY_ID'),
                "private_key": os.environ.get('GOOGLE_PRIVATE_KEY').replace('\\n', '\n'),
                "client_email": os.environ.get('GOOGLE_CLIENT_EMAIL'),
                "client_id": os.environ.get('GOOGLE_CLIENT_ID'),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{os.environ.get('GOOGLE_CLIENT_EMAIL')}"
            }
            creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        else:
            creds = Credentials.from_service_account_file('creds.json', scopes=SCOPES)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        return spreadsheet.worksheet(sheet_name)
    except Exception as e:
        print(f"Sheet error ({sheet_name}): {e}")
        return None

# ── DECORATORS ──
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user' not in session:
                return redirect(url_for('login'))
            if session.get('role') not in roles:
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated
    return decorator

# ── PWA ──
@app.route('/manifest.json')
def manifest():
    return send_from_directory('.', 'manifest.json',
                               mimetype='application/manifest+json')

@app.route('/sw.js')
def service_worker():
    return send_from_directory('.', 'sw.js',
                               mimetype='application/javascript')

# ══════════════════════════════════════
#   LOGIN / LOGOUT
# ══════════════════════════════════════

@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username  = request.form.get('username', '').strip()
        password  = request.form.get('password', '').strip()
        role_type = request.form.get('role', 'staff')

        if role_type == 'staff':
            staff_users = {
                'admin':      {'password': '12345',  'role': 'admin'},
                'fee':        {'password': 'fee123', 'role': 'fee'},
                'attendance': {'password': 'att123', 'role': 'attendance'},
                'grades':     {'password': 'grd123', 'role': 'grades'},
            }
            if username.lower() in staff_users:
                user = staff_users[username.lower()]
                if user['password'] == password:
                    session['user'] = username
                    session['role'] = user['role']
                    session['name'] = username.title()
                    return redirect(url_for('dashboard'))
            return render_template('login.html', error='Invalid username or password!')

        else:
            sheet = get_sheet('students')
            if sheet:
                students = sheet.get_all_records()
                for student in students:
                    if (str(student.get('ID', '')) == username and
                            str(student.get('Password', '')) == password):
                        session['user']       = username
                        session['role']       = 'student'
                        session['name']       = student.get('Name', '')
                        session['class']      = str(student.get('Class', ''))
                        session['student_id'] = student.get('ID', '')
                        return redirect(url_for('dashboard'))
            return render_template('login.html', error='Invalid Student ID or password!')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ══════════════════════════════════════
#   DASHBOARD
# ══════════════════════════════════════

@app.route('/dashboard')
@login_required
def dashboard():
    role = session.get('role')
    name = session.get('name')

    if role == 'student':
        student_id   = session.get('student_id')
        sheet        = get_sheet('students')
        student_data = {}
        if sheet:
            students = sheet.get_all_records()
            for s in students:
                if str(s.get('ID', '')) == student_id:
                    student_data = s
                    break
        return render_template('dashboard.html',
                               role=role, name=name,
                               student=student_data)

    elif role == 'admin':
        students_sheet = get_sheet('students')
        total_students = 0
        if students_sheet:
            all_s = students_sheet.get_all_records()
            total_students = len([s for s in all_s
                                  if s.get('ID') and
                                  str(s.get('ID', '')).startswith('CS')])

        fees_sheet      = get_sheet('fees')
        total_collected = 0
        if fees_sheet:
            fees = fees_sheet.get_all_records()
            for f in fees:
                try:
                    total_collected += float(f.get('Amount_Paid', 0) or 0)
                except:
                    pass

        attendance_sheet = get_sheet('attendance')
        attendance_rate  = 0
        if attendance_sheet:
            records = attendance_sheet.get_all_records()
            if records:
                present = len([r for r in records
                               if r.get('Status') == 'Present'])
                attendance_rate = round((present / len(records)) * 100, 1)

        return render_template('dashboard.html',
                               role=role, name=name,
                               total_students=total_students,
                               total_collected=total_collected,
                               attendance_rate=attendance_rate)
    else:
        return render_template('dashboard.html', role=role, name=name)

# ══════════════════════════════════════
#   STUDENTS
# ══════════════════════════════════════

@app.route('/students')
@login_required
def students():
    role   = session.get('role')
    search = request.args.get('search', '').lower()

    sheet        = get_sheet('students')
    all_students = []
    if sheet:
        records      = sheet.get_all_records()
        all_students = [s for s in records
                        if s.get('ID') and
                        str(s.get('ID', '')).startswith('CS')]
        if search:
            all_students = [s for s in all_students if
                            search in str(s.get('ID', '')).lower() or
                            search in str(s.get('Name', '')).lower() or
                            search in str(s.get('Class', '')).lower()]

    return render_template('students.html',
                           role=role,
                           name=session.get('name'),
                           students=all_students,
                           search=search)

@app.route('/add_student', methods=['POST'])
@role_required('admin')
def add_student():
    try:
        name      = request.form.get('name', '').strip()
        class_    = request.form.get('class', '').strip()
        phone     = request.form.get('phone', '').strip()
        total_fee = request.form.get('total_fee', '0').strip()

        sheet = get_sheet('students')
        if not sheet:
            return jsonify({'success': False, 'message': 'Sheet error'})

        records        = sheet.get_all_records()
        class_students = [r for r in records
                          if str(r.get('Class', '')) == class_ and
                          str(r.get('ID', '')).startswith('CS')]
        next_num    = len(class_students) + 1
        student_id  = f"CS{class_}{next_num:02d}"
        name_part   = name[:3].lower().replace(' ', '')
        password    = f"{name_part}{next_num:03d}"

        new_row = [
            student_id, name, class_, phone, password,
            total_fee, 0, total_fee,
            datetime.now().strftime('%Y-%m-%d')
        ]
        sheet.append_row(new_row, value_input_option='RAW')
        return jsonify({
            'success': True,
            'message': f'Student added! ID: {student_id}, Password: {password}'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/edit_student', methods=['POST'])
@role_required('admin')
def edit_student():
    try:
        data       = request.get_json()
        student_id = data.get('student_id')
        name       = data.get('name', '').strip()
        class_     = data.get('class', '').strip()
        phone      = data.get('phone', '').strip()
        total_fee  = data.get('total_fee', '0')

        sheet = get_sheet('students')
        if not sheet:
            return jsonify({'success': False, 'message': 'Sheet error'})

        records = sheet.get_all_records()
        for i, record in enumerate(records, start=2):
            if str(record.get('ID', '')) == student_id:
                current_paid = float(record.get('Amount_Paid', 0) or 0)
                new_balance  = float(total_fee) - current_paid
                if new_balance < 0:
                    new_balance = 0

                sheet.update_cell(i, 2, name)
                sheet.update_cell(i, 3, class_)
                sheet.update_cell(i, 4, phone)
                sheet.update_cell(i, 6, total_fee)
                sheet.update_cell(i, 8, new_balance)

                return jsonify({'success': True,
                                'message': 'Student updated!'})

        return jsonify({'success': False, 'message': 'Student not found'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/delete_student', methods=['POST'])
@role_required('admin')
def delete_student():
    try:
        data       = request.get_json()
        student_id = data.get('student_id')

        sheet = get_sheet('students')
        if not sheet:
            return jsonify({'success': False})

        records = sheet.get_all_records()
        for i, record in enumerate(records, start=2):
            if str(record.get('ID', '')) == student_id:
                sheet.delete_rows(i)
                return jsonify({'success': True})

        return jsonify({'success': False, 'message': 'Student not found'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/search_student')
@login_required
def search_student():
    query = request.args.get('q', '').lower()
    sheet = get_sheet('students')
    results = []

    if sheet and query:
        records = sheet.get_all_records()
        results = [s for s in records
                   if s.get('ID') and
                   str(s.get('ID', '')).startswith('CS') and
                   (query in str(s.get('ID', '')).lower() or
                    query in str(s.get('Name', '')).lower() or
                    query in str(s.get('Class', '')).lower())]

    return jsonify({'students': results})

# ══════════════════════════════════════
#   ATTENDANCE
# ══════════════════════════════════════

@app.route('/attendance')
@login_required
def attendance():
    role           = session.get('role')
    selected_class = request.args.get('class', '')
    today          = datetime.now().strftime('%Y-%m-%d')
    class_students = []
    already_taken  = False

    if role == 'student':
        student_id  = session.get('student_id')
        att_sheet   = get_sheet('attendance')
        att_records = []
        if att_sheet:
            records     = att_sheet.get_all_records()
            att_records = [r for r in records
                           if str(r.get('Student_ID', '')) == student_id]
        return render_template('attendance.html',
                               role=role,
                               name=session.get('name'),
                               students=att_records,
                               today=today,
                               selected_class='',
                               already_taken=False)

    if selected_class:
        students_sheet = get_sheet('students')
        if students_sheet:
            all_s          = students_sheet.get_all_records()
            class_students = [s for s in all_s
                              if str(s.get('Class', '')) == selected_class
                              and s.get('ID')
                              and str(s.get('ID', '')).startswith('CS')]

        att_sheet = get_sheet('attendance')
        if att_sheet:
            records       = att_sheet.get_all_records()
            today_records = [r for r in records
                             if r.get('Date') == today and
                             str(r.get('Class', '')) == selected_class]
            already_taken = len(today_records) > 0

    return render_template('attendance.html',
                           role=role,
                           name=session.get('name'),
                           selected_class=selected_class,
                           students=class_students,
                           already_taken=already_taken,
                           today=today)

@app.route('/submit_attendance', methods=['POST'])
@role_required('admin', 'attendance')
def submit_attendance():
    try:
        data            = request.get_json()
        class_          = data.get('class')
        attendance_data = data.get('attendance', [])
        today           = datetime.now().strftime('%Y-%m-%d')

        sheet = get_sheet('attendance')
        if not sheet:
            return jsonify({'success': False})

        records       = sheet.get_all_records()
        today_records = [r for r in records
                         if r.get('Date') == today and
                         str(r.get('Class', '')) == class_]
        if today_records:
            return jsonify({'success': False,
                            'message': 'Attendance already taken today!'})

        for att in attendance_data:
            sheet.append_row([
                today,
                att.get('student_id'),
                att.get('student_name'),
                class_,
                att.get('status')
            ], value_input_option='RAW')

        return jsonify({'success': True,
                        'message': 'Attendance saved!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# ══════════════════════════════════════
#   FEES
# ══════════════════════════════════════

@app.route('/fees')
@login_required
def fees():
    role   = session.get('role')
    search = request.args.get('search', '').lower()

    if role == 'student':
        student_id = session.get('student_id')
        sheet      = get_sheet('students')
        student    = []
        if sheet:
            records = sheet.get_all_records()
            student = [s for s in records
                       if str(s.get('ID', '')) == student_id]
        return render_template('fees.html',
                               role=role,
                               name=session.get('name'),
                               students=student,
                               search='')

    sheet        = get_sheet('students')
    all_students = []
    if sheet:
        records      = sheet.get_all_records()
        all_students = [s for s in records
                        if s.get('ID') and
                        str(s.get('ID', '')).startswith('CS')]
        if search:
            all_students = [s for s in all_students if
                            search in str(s.get('ID', '')).lower() or
                            search in str(s.get('Name', '')).lower()]

    return render_template('fees.html',
                           role=role,
                           name=session.get('name'),
                           students=all_students,
                           search=search)

@app.route('/pay_fee', methods=['POST'])
@role_required('admin', 'fee')
def pay_fee():
    try:
        data       = request.get_json()
        student_id = data.get('student_id')
        amount     = float(data.get('amount', 0))

        sheet = get_sheet('students')
        if not sheet:
            return jsonify({'success': False, 'message': 'Sheet error'})

        records = sheet.get_all_records()
        for i, record in enumerate(records, start=2):
            if str(record.get('ID', '')) == student_id:
                current_paid = float(record.get('Amount_Paid', 0) or 0)
                total_fee    = float(record.get('Total_Fee', 0) or 0)
                new_paid     = current_paid + amount
                new_balance  = total_fee - new_paid
                if new_balance < 0:
                    new_balance = 0

                sheet.update_cell(i, 7, new_paid)
                sheet.update_cell(i, 8, new_balance)

                fees_sheet = get_sheet('fees')
                if fees_sheet:
                    fees_sheet.append_row([
                        datetime.now().strftime('%Y-%m-%d'),
                        student_id,
                        record.get('Name', ''),
                        str(record.get('Class', '')),
                        amount,
                        total_fee,
                        new_balance
                    ], value_input_option='RAW')

                return jsonify({
                    'success': True,
                    'new_paid': new_paid,
                    'new_balance': new_balance,
                    'message': f'Payment ${amount} recorded! Balance: ${new_balance}'
                })

        return jsonify({'success': False, 'message': 'Student not found'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/edit_fee', methods=['POST'])
@role_required('admin', 'fee')
def edit_fee():
    try:
        data       = request.get_json()
        student_id = data.get('student_id')
        total_fee  = float(data.get('total_fee', 0))

        sheet = get_sheet('students')
        if not sheet:
            return jsonify({'success': False})

        records = sheet.get_all_records()
        for i, record in enumerate(records, start=2):
            if str(record.get('ID', '')) == student_id:
                current_paid = float(record.get('Amount_Paid', 0) or 0)
                new_balance  = total_fee - current_paid
                if new_balance < 0:
                    new_balance = 0

                sheet.update_cell(i, 6, total_fee)
                sheet.update_cell(i, 8, new_balance)

                return jsonify({
                    'success': True,
                    'new_balance': new_balance,
                    'message': 'Fee updated!'
                })

        return jsonify({'success': False, 'message': 'Student not found'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# ══════════════════════════════════════
#   GRADES
# ══════════════════════════════════════

@app.route('/grades')
@login_required
def grades():
    role   = session.get('role')
    search = request.args.get('search', '').lower()

    if role == 'student':
        student_id     = session.get('student_id')
        sheet          = get_sheet('grades')
        student_grades = {'Term1': {}, 'Term2': {}}

        if sheet:
            records = sheet.get_all_records()
            for r in records:
                if str(r.get('Student_ID', '')) == student_id:
                    subject = r.get('Subject', '')
                    term    = r.get('Term', '')
                    score   = r.get('Score', 0)
                    if term in student_grades:
                        student_grades[term][subject] = score

        def calc_avg(term_grades):
            scores = [float(v) for v in term_grades.values() if v]
            return round(sum(scores) / len(scores), 1) if scores else 0

        t1_avg = calc_avg(student_grades['Term1'])
        t2_avg = calc_avg(student_grades['Term2'])

        # Final: haddii Term2 la gaarin, Term1 kaliya
        if t1_avg and t2_avg:
            final = round((t1_avg + t2_avg) / 2, 1)
        elif t1_avg:
            final = t1_avg
        else:
            final = 0

        has_term1 = len(student_grades['Term1']) > 0
        has_term2 = len(student_grades['Term2']) > 0

        return render_template('grades.html',
                               role=role,
                               name=session.get('name'),
                               grades=student_grades,
                               subjects=SUBJECTS,
                               t1_avg=t1_avg,
                               t2_avg=t2_avg,
                               final=final,
                               has_term1=has_term1,
                               has_term2=has_term2)

    sheet        = get_sheet('students')
    all_students = []
    if sheet:
        records      = sheet.get_all_records()
        all_students = [s for s in records
                        if s.get('ID') and
                        str(s.get('ID', '')).startswith('CS')]
        if search:
            all_students = [s for s in all_students if
                            search in str(s.get('ID', '')).lower() or
                            search in str(s.get('Name', '')).lower()]

    return render_template('grades.html',
                           role=role,
                           name=session.get('name'),
                           students=all_students,
                           subjects=SUBJECTS,
                           search=search)

@app.route('/save_grades', methods=['POST'])
@role_required('admin', 'grades')
def save_grades():
    try:
        data         = request.get_json()
        student_id   = data.get('student_id')
        student_name = data.get('student_name')
        class_       = data.get('class')
        term         = data.get('term')
        grades_data  = data.get('grades', {})
        today        = datetime.now().strftime('%Y-%m-%d')

        sheet = get_sheet('grades')
        if not sheet:
            return jsonify({'success': False})

        records        = sheet.get_all_records()
        rows_to_delete = []
        for i, r in enumerate(records, start=2):
            if (str(r.get('Student_ID', '')) == student_id and
                    r.get('Term', '') == term):
                rows_to_delete.append(i)

        for row in sorted(rows_to_delete, reverse=True):
            sheet.delete_rows(row)

        for subject, score in grades_data.items():
            sheet.append_row([
                student_id, student_name, class_,
                subject, score, term, today
            ], value_input_option='RAW')

        return jsonify({'success': True, 'message': 'Grades saved!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/get_student_grades')
@login_required
def get_student_grades():
    student_id = request.args.get('student_id')
    sheet      = get_sheet('grades')
    grades     = {'Term1': {}, 'Term2': {}}

    if sheet and student_id:
        records = sheet.get_all_records()
        for r in records:
            if str(r.get('Student_ID', '')) == student_id:
                subject = r.get('Subject', '')
                term    = r.get('Term', '')
                score   = r.get('Score', 0)
                if term in grades:
                    grades[term][subject] = score

    return jsonify(grades)

# ══════════════════════════════════════
#   VOTES
# ══════════════════════════════════════

@app.route('/votes')
@login_required
def votes():
    role = session.get('role')

    sheet         = get_sheet('candidates')
    candidates    = []
    election_open = False

    if sheet:
        records    = sheet.get_all_records()
        candidates = [c for c in records if c.get('Candidate_ID')]
        if candidates:
            election_open = str(
                candidates[0].get('Election_Status', 'closed')
            ).lower() == 'open'

    # Check already voted + who voted for
    already_voted  = False
    voted_for      = None
    if role == 'student':
        student_id  = session.get('student_id')
        votes_sheet = get_sheet('votes')
        if votes_sheet:
            vote_records = votes_sheet.get_all_records()
            for v in vote_records:
                if str(v.get('Student_ID', '')) == student_id:
                    already_voted = True
                    voted_for     = str(v.get('Candidate_ID', ''))
                    break

    total_votes = sum(int(c.get('Votes', 0) or 0) for c in candidates)
    for c in candidates:
        votes_count     = int(c.get('Votes', 0) or 0)
        c['percentage'] = round(
            (votes_count / total_votes * 100), 1
        ) if total_votes > 0 else 0

    # Sort by votes for results
    sorted_candidates = sorted(candidates,
                                key=lambda x: int(x.get('Votes', 0) or 0),
                                reverse=True)
    winner = sorted_candidates[0] if sorted_candidates and total_votes > 0 else None

    return render_template('votes.html',
                           role=role,
                           name=session.get('name'),
                           candidates=candidates,
                           sorted_candidates=sorted_candidates,
                           election_open=election_open,
                           already_voted=already_voted,
                           voted_for=voted_for,
                           total_votes=total_votes,
                           winner=winner)

@app.route('/submit_vote', methods=['POST'])
@role_required('student')
def submit_vote():
    try:
        data         = request.get_json()
        candidate_id = data.get('candidate_id')
        student_id   = session.get('student_id')

        votes_sheet = get_sheet('votes')
        if not votes_sheet:
            return jsonify({'success': False, 'message': 'Error!'})

        # HAL COD KALIYA
        vote_records  = votes_sheet.get_all_records()
        student_votes = [v for v in vote_records
                         if str(v.get('Student_ID', '')) == student_id]
        if len(student_votes) >= 1:
            return jsonify({'success': False,
                            'message': 'You have already voted!'})

        votes_sheet.append_row([
            student_id,
            candidate_id,
            datetime.now().strftime('%Y-%m-%d')
        ], value_input_option='RAW')

        candidates_sheet = get_sheet('candidates')
        if candidates_sheet:
            records = candidates_sheet.get_all_records()
            for i, c in enumerate(records, start=2):
                if str(c.get('Candidate_ID', '')) == candidate_id:
                    current_votes = int(c.get('Votes', 0) or 0)
                    candidates_sheet.update_cell(i, 4, current_votes + 1)
                    break

        return jsonify({'success': True,
                        'message': 'Vote submitted! 🎉'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/toggle_election', methods=['POST'])
@role_required('admin')
def toggle_election():
    try:
        data   = request.get_json()
        status = data.get('status', 'closed')

        sheet = get_sheet('candidates')
        if sheet:
            records = sheet.get_all_records()
            for i, c in enumerate(records, start=2):
                sheet.update_cell(i, 5, status)

        return jsonify({'success': True, 'status': status})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/add_candidate', methods=['POST'])
@role_required('admin')
def add_candidate():
    try:
        candidate_id = request.form.get('candidate_id', '').strip()
        name         = request.form.get('name', '').strip()
        class_       = request.form.get('class', '').strip()
        photo        = request.files.get('photo')

        if not candidate_id or not name:
            return jsonify({'success': False, 'message': 'ID and Name required!'})

        sheet = get_sheet('candidates')
        if not sheet:
            return jsonify({'success': False})

        if photo and photo.filename:
            filename = f"{candidate_id}.jpg"
            filepath = os.path.join('static', 'images', 'candidates', filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            photo.save(filepath)

        sheet.append_row([
            candidate_id, name, class_, 0, 'closed'
        ], value_input_option='RAW')

        return jsonify({'success': True, 'message': 'Candidate added!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/update_candidate', methods=['POST'])
@role_required('admin')
def update_candidate():
    try:
        candidate_id = request.form.get('candidate_id', '').strip()
        name         = request.form.get('name', '').strip()
        class_       = request.form.get('class', '').strip()
        photo        = request.files.get('photo')

        sheet = get_sheet('candidates')
        if not sheet:
            return jsonify({'success': False})

        records = sheet.get_all_records()
        for i, c in enumerate(records, start=2):
            if str(c.get('Candidate_ID', '')) == candidate_id:
                sheet.update_cell(i, 2, name)
                sheet.update_cell(i, 3, class_)
                if photo and photo.filename:
                    filename = f"{candidate_id}.jpg"
                    filepath = os.path.join('static', 'images', 'candidates', filename)
                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                    photo.save(filepath)
                return jsonify({'success': True, 'message': 'Updated!'})

        return jsonify({'success': False, 'message': 'Not found'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/delete_candidate', methods=['POST'])
@role_required('admin')
def delete_candidate():
    try:
        data         = request.get_json()
        candidate_id = data.get('candidate_id')

        sheet = get_sheet('candidates')
        if not sheet:
            return jsonify({'success': False})

        records = sheet.get_all_records()
        for i, c in enumerate(records, start=2):
            if str(c.get('Candidate_ID', '')) == candidate_id:
                sheet.delete_rows(i)
                return jsonify({'success': True})

        return jsonify({'success': False, 'message': 'Not found'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# ══════════════════════════════════════
#   ANNOUNCEMENT
# ══════════════════════════════════════

@app.route('/announcement')
@login_required
def announcement():
    role = session.get('role')
    try:
        sheet             = get_sheet('users')
        announcement_text = ''
        if sheet:
            try:
                ann_cell          = sheet.acell('E1').value
                announcement_text = ann_cell or ''
            except:
                announcement_text = ''
    except:
        announcement_text = ''

    return render_template('announcement.html',
                           role=role,
                           name=session.get('name'),
                           announcement=announcement_text)

@app.route('/save_announcement', methods=['POST'])
@role_required('admin')
def save_announcement():
    try:
        data  = request.get_json()
        text  = data.get('text', '')
        sheet = get_sheet('users')
        if sheet:
            sheet.update_acell('E1', text)
        return jsonify({'success': True, 'message': 'Saved!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# ══════════════════════════════════════
#   PHOTO UPLOAD
# ══════════════════════════════════════

@app.route('/upload_photo', methods=['POST'])
@role_required('student')
def upload_photo():
    try:
        if 'photo' not in request.files:
            return jsonify({'success': False, 'message': 'No file'})

        file       = request.files['photo']
        student_id = session.get('student_id')
        filename   = f"{student_id}.jpg"
        filepath   = os.path.join('static', 'images', 'students', filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        file.save(filepath)

        return jsonify({
            'success': True,
            'photo_url': f'/static/images/students/{filename}'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# ══════════════════════════════════════
#   RUN
# ══════════════════════════════════════

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
