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
try:
    import qrcode
    import qrcode.image.svg
    import io
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False

app = Flask(__name__)
app.secret_key = 'school_system_secret_key_2026'

# ── COMPRESSION ──
try:
    from flask_compress import Compress
    Compress(app)
except ImportError:
    pass

# ── PERFORMANCE HEADERS ──
@app.after_request
def perf_headers(response):
    # Cache static files aggressively
    if request.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'public, max-age=86400'
    else:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    # Speed headers
    response.headers['X-Content-Type-Options']   = 'nosniff'
    response.headers['Vary']                      = 'Accept-Encoding'
    return response

# Speed: warm up Google Sheets connection in background on startup
import time
import threading

def _warmup():
    try:
        time.sleep(1)  # wait for app to init
        _init_gspread()
        get_sheet_cached('students')
        print("Cache warmed up: students sheet ready")
    except Exception as e:
        print(f"Warmup error: {e}")
threading.Thread(target=_warmup, daemon=True).start()

# Server-side sheet cache - reduces Google Sheets API calls
_SHEET_CACHE = {}
_SHEET_CACHE_TTL = 120  # seconds — 2 min cache reduces API calls significantly

def get_sheet_cached(name):
    now = time.time()
    key = 'records_' + name
    if key in _SHEET_CACHE:
        entry = _SHEET_CACHE[key]
        if now - entry['ts'] < _SHEET_CACHE_TTL:
            return entry['data']
    sheet = get_sheet(name)
    if not sheet:
        return []
    try:
        records = sheet.get_all_records()
        _SHEET_CACHE[key] = {'data': records, 'ts': now}
        return records
    except Exception as e:
        print(f"Sheet cache error: {e}")
        return []

def invalidate_cache(name=None):
    global _SHEET_CACHE
    if name:
        key = 'records_' + name
        _SHEET_CACHE.pop(key, None)
    else:
        _SHEET_CACHE.clear()



SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

SPREADSHEET_ID = '1dRrx8QUq8XpBiP8TzPb85ObL95LgkDQZI6M72NBbGag'

SUBJECTS = [
    'Quranka', 'Xisaab', 'Somali', 'English', 'Science',
    'Social Studies', 'Arabic', 'Islamic Studies', 'Computer', 'P.E.'
]

# 13 Classes
CLASSES = ['Xaddaano','1','2','3','4','5','6','7','8','Form One','Form Two','Form Three','Form Four']

CLASS_DISPLAY = {
    'Xaddaano':'Xaddaano','1':'Class 1','2':'Class 2','3':'Class 3','4':'Class 4',
    '5':'Class 5','6':'Class 6','7':'Class 7','8':'Class 8',
    'Form One':'Form One','Form Two':'Form Two','Form Three':'Form Three','Form Four':'Form Four'
}

CLASS_ORDER = {
    'Xaddaano':0,'1':1,'2':2,'3':3,'4':4,'5':5,'6':6,'7':7,'8':8,
    'Form One':9,'Form Two':10,'Form Three':11,'Form Four':12
}

NEXT_CLASS = {
    'Xaddaano':'1','1':'2','2':'3','3':'4','4':'5','5':'6',
    '6':'7','7':'8','8':'Form One','Form One':'Form Two',
    'Form Two':'Form Three','Form Three':'Form Four'
}

def get_id_prefix(cls):
    m = {'Xaddaano':'CS0','1':'CS1','2':'CS2','3':'CS3','4':'CS4','5':'CS5',
         '6':'CS6','7':'CS7','8':'CS8','Form One':'CS9','Form Two':'CS10',
         'Form Three':'CS11','Form Four':'CS12'}
    return m.get(str(cls).strip(), 'CS')

def class_display(cls):
    return CLASS_DISPLAY.get(str(cls).strip(), str(cls))

def get_active_school_year():
    yr = datetime.now().year
    return os.environ.get('SCHOOL_YEAR', f"{yr}-{yr+1}")


# ── GOOGLE SHEETS ──
# ── PERSISTENT GSPREAD CLIENT — authenticate ONCE, reuse for all calls ──
_GSPREAD_CLIENT      = None
_GSPREAD_SPREADSHEET = None
_GSPREAD_WORKSHEETS  = {}
_GSPREAD_INIT_TIME   = 0

def _init_gspread():
    global _GSPREAD_CLIENT, _GSPREAD_SPREADSHEET, _GSPREAD_INIT_TIME, _GSPREAD_WORKSHEETS
    now = time.time()
    if _GSPREAD_CLIENT and (now - _GSPREAD_INIT_TIME) < 3300:  # reuse for 55 min
        return True
    try:
        if os.environ.get('GOOGLE_PRIVATE_KEY'):
            creds_info = {
                "type": os.environ.get('GOOGLE_TYPE','service_account'),
                "project_id": os.environ.get('GOOGLE_PROJECT_ID'),
                "private_key_id": os.environ.get('GOOGLE_PRIVATE_KEY_ID'),
                "private_key": os.environ.get('GOOGLE_PRIVATE_KEY').replace('\\n','\n'),
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
        _GSPREAD_CLIENT      = gspread.authorize(creds)
        _GSPREAD_SPREADSHEET = _GSPREAD_CLIENT.open_by_key(SPREADSHEET_ID)
        _GSPREAD_WORKSHEETS  = {}
        _GSPREAD_INIT_TIME   = now
        print("gspread: authenticated OK")
        return True
    except Exception as e:
        print(f"gspread auth error: {e}")
        return False

def get_sheet(sheet_name):
    global _GSPREAD_WORKSHEETS, _GSPREAD_CLIENT
    try:
        if not _init_gspread():
            return None
        # Return cached worksheet object
        if sheet_name in _GSPREAD_WORKSHEETS:
            return _GSPREAD_WORKSHEETS[sheet_name]
        ws = _GSPREAD_SPREADSHEET.worksheet(sheet_name)
        _GSPREAD_WORKSHEETS[sheet_name] = ws
        return ws
    except gspread.WorksheetNotFound:
        try:
            ws = _GSPREAD_SPREADSHEET.add_worksheet(sheet_name, 1000, 20)
            _GSPREAD_WORKSHEETS[sheet_name] = ws
            return ws
        except Exception:
            return None
    except Exception as e:
        print(f"Sheet error ({sheet_name}): {e}")
        _GSPREAD_CLIENT = None  # force re-auth next time
        _GSPREAD_WORKSHEETS = {}
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
            # Read staff from Google Sheets 'users' sheet: A=Username, B=Password, C=Role, D=Name
            matched_staff = False
            try:
                users_sheet = get_sheet('users')
                if users_sheet:
                    records = users_sheet.get_all_records()
                    print(f"users sheet records: {records}")  # debug
                    for u in records:
                        u_user = str(u.get('Username', '')).strip()
                        u_pass = str(u.get('Password', '')).strip()
                        u_role = str(u.get('Role',     '')).strip().lower()
                        u_name = str(u.get('Name',     '')).strip()
                        print(f"Checking: '{u_user}' vs '{username}', '{u_pass}' vs '{password}'")
                        if u_user.lower() == username.strip().lower() and u_pass == password.strip():
                            session['user'] = username
                            session['role'] = u_role
                            session['name'] = u_name or username.title()
                            matched_staff = True
                            break
            except Exception as e:
                print(f"users sheet login error: {e}")
            
            # Fallback: if sheet failed or no match, try hardcoded defaults
            if not matched_staff:
                fallback = {
                    'admin':      {'password': '12345',  'role': 'admin',      'name': 'Administrator'},
                    'fee':        {'password': 'fee123', 'role': 'fee',        'name': 'Fee Admin'},
                    'attendance': {'password': 'att123', 'role': 'attendance', 'name': 'Attendance Admin'},
                    'grades':     {'password': 'grd123', 'role': 'grades',     'name': 'Grades Admin'},
                }
                u = fallback.get(username.strip().lower())
                if u and u['password'] == password.strip():
                    session['user'] = username
                    session['role'] = u['role']
                    session['name'] = u['name']
                    matched_staff = True
                    print(f"Fallback login used for: {username}")

            if matched_staff:
                return redirect(url_for('dashboard'))
            return render_template('login.html', error='Invalid username or password!')

        else:
            # Use cache for fast login — avoids cold API call on every login
            students = get_sheet_cached('students')
            matched = False
            for student in students:
                if (str(student.get('ID', '')) == username and
                        str(student.get('Password', '')) == password):
                    session['user']       = username
                    session['role']       = 'student'
                    session['name']       = student.get('Name', '')
                    session['class']      = str(student.get('Class', ''))
                    session['class_display'] = class_display(str(student.get('Class', '')))
                    session['student_id'] = student.get('ID', '')
                    matched = True
                    break
            if matched:
                return redirect(url_for('dashboard'))
            # If cache miss, try direct sheet
            if not students:
                sheet = get_sheet('students')
                if sheet:
                    students_direct = sheet.get_all_records()
                    for student in students_direct:
                        if (str(student.get('ID',''))==username and
                                str(student.get('Password',''))==password):
                            session['user']       = username
                            session['role']       = 'student'
                            session['name']       = student.get('Name','')
                            session['class']      = str(student.get('Class',''))
                            session['student_id'] = student.get('ID','')
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
        student_id   = session.get('student_id','')
        # Use cached records — instant response
        all_students = get_sheet_cached('students')
        student_data = {}
        for s in all_students:
            if str(s.get('ID','')).strip() == student_id:
                student_data = s
                session['class'] = str(s.get('Class',''))
                break
        return render_template('dashboard.html',
                               role=role, name=name,
                               student=student_data)

    elif role == 'admin':
        total_students = 0
        all_students_data = []
        # Try cached first, fallback to live
        all_s = get_sheet_cached('students') or []
        if not all_s:
            try:
                sh = get_sheet('students')
                all_s = sh.get_all_records() if sh else []
            except: all_s = []
        if all_s:
            cs_students = [s for s in all_s if s.get('ID') and str(s.get('ID','')).startswith('CS')]
            total_students = len(cs_students)
            for s in cs_students:
                # Read fee data directly from students sheet — no extra API call
                all_students_data.append({
                    'ID':          str(s.get('ID','')).strip(),
                    'Name':        str(s.get('Name','')).strip(),
                    'Class':       str(s.get('Class','')).strip(),
                    'Phone':       str(s.get('Phone','')).strip(),
                    'Total_Fee':   float(s.get('Total_Fee',0) or 0),
                    'Amount_Paid': float(s.get('Amount_Paid',0) or 0),
                    'Balance':     float(s.get('Balance',0) or 0),
                    'Status':      str(s.get('Status','Active')).strip(),
                    'Enrollment_Date': str(s.get('Enrollment_Date','')).strip(),
                })

        # total_collected = sum of Amount_Paid from students sheet directly
        total_collected = round(sum(s['Amount_Paid'] for s in all_students_data), 2)

        attendance_sheet = get_sheet('attendance')
        attendance_rate  = 0
        if attendance_sheet:
            records = attendance_sheet.get_all_records()
            if records:
                present = len([r for r in records if r.get('Status') == 'Present'])
                attendance_rate = round((present / len(records)) * 100, 1)

        return render_template('dashboard.html',
                               role=role, name=name,
                               total_students=total_students,
                               total_collected=total_collected,
                               attendance_rate=attendance_rate,
                               all_students=all_students_data,
                               classes=CLASSES,
                               class_display_map=CLASS_DISPLAY,
                               school_year=get_active_school_year())
    else:
        return render_template('dashboard.html', role=role, name=name,
                               classes=CLASSES,
                               school_year=get_active_school_year())

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

        records  = sheet.get_all_records()
        # Get prefix for this class
        prefix = get_id_prefix(class_)
        # Find max existing sequence for this prefix
        existing_nums = []
        for r in records:
            rid = str(r.get('ID','')).strip()
            if rid.startswith(prefix):
                try:
                    num_part = rid[len(prefix):]
                    existing_nums.append(int(num_part))
                except:
                    pass
        next_num   = (max(existing_nums) + 1) if existing_nums else 1
        student_id = f"{prefix}{next_num:02d}"
        password   = f"{student_id.lower()}1"

        new_row = [
            student_id, name, class_, phone, password,
            total_fee, 0, total_fee,
            datetime.now().strftime('%Y-%m-%d'),
            'Active'
        ]
        sheet.append_row(new_row, value_input_option='RAW')
        invalidate_cache('students')
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
        data            = request.get_json()
        student_id      = str(data.get('student_id', '')).strip()
        name            = data.get('name', '').strip()
        class_          = str(data.get('class', '')).strip()
        phone           = data.get('phone', '').strip()
        enrollment_date = data.get('enrollment_date', '').strip()
        total_fee_raw   = str(data.get('total_fee', '')).strip()

        if not student_id or not name:
            return jsonify({'success': False, 'message': 'ID and Name required'})

        sheet = get_sheet('students')
        if not sheet:
            return jsonify({'success': False, 'message': 'Google Sheet connection error'})

        records = sheet.get_all_records()
        for i, record in enumerate(records, start=2):
            if str(record.get('ID', '')).strip() == student_id:
                # Keep existing total_fee if not provided from ID card form
                existing_fee = str(record.get('Total_Fee', '0') or '0').strip()
                try:
                    total_fee = float(total_fee_raw) if total_fee_raw else float(existing_fee or 0)
                except (ValueError, TypeError):
                    total_fee = float(existing_fee or 0)

                try:
                    current_paid = float(str(record.get('Amount_Paid', 0) or 0))
                except (ValueError, TypeError):
                    current_paid = 0.0
                new_balance = max(0.0, total_fee - current_paid)

                # Batch update — single API call for speed
                current_password = record.get('Password', '')
                current_status   = record.get('Status', 'Active')
                if enrollment_date:
                    sheet.update(f'B{i}:J{i}', [[name, class_, phone, current_password,
                                                  total_fee, current_paid, new_balance,
                                                  enrollment_date, current_status]])
                else:
                    sheet.update(f'B{i}:H{i}', [[name, class_, phone, current_password,
                                                  total_fee, current_paid, new_balance]])

                invalidate_cache('students')
                invalidate_cache('grades')
                return jsonify({'success': True, 'message': 'Student updated in Google Sheet!'})

        return jsonify({'success': False, 'message': f'Student {student_id} not found in sheet'})
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
    query = request.args.get('q', '').lower().strip()
    records = get_sheet_cached('students') or []
    results = []
    if records and query:
        for s in records:
            sid = str(s.get('ID','')).strip()
            if not sid.startswith('CS'):
                continue
            sname = str(s.get('Name','')).lower()
            scls  = str(s.get('Class','')).lower()
            if query in sid.lower() or query in sname or query in scls:
                results.append({
                    'ID':          sid,
                    'Name':        str(s.get('Name','')).strip(),
                    'Class':       str(s.get('Class','')).strip(),
                    'Phone':       str(s.get('Phone','')).strip(),
                    'Total_Fee':   float(s.get('Total_Fee',0) or 0),
                    'Amount_Paid': float(s.get('Amount_Paid',0) or 0),
                    'Balance':     float(s.get('Balance',0) or 0),
                    'Status':      str(s.get('Status','Active')).strip(),
                    'Enrollment_Date': str(s.get('Enrollment_Date','')).strip(),
                })
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
        student_id  = str(session.get('student_id','')).strip()
        att_records = []
        try:
            att_sheet = get_sheet('attendance')
            if att_sheet and student_id:
                # Use raw values — col C (index 2) = Student_ID
                att_vals = att_sheet.get_all_values()
                for row in att_vals[1:]:
                    if len(row) < 3: continue
                    sid = str(row[2]).strip()
                    if sid == student_id:
                        att_records.append({
                            'Date':         row[0] if len(row)>0 else '',
                            'Time':         row[1] if len(row)>1 else '',
                            'Student_ID':   sid,
                            'Student_Name': row[3] if len(row)>3 else '',
                            'Class':        row[4] if len(row)>4 else '',
                            'Subject':      row[5] if len(row)>5 else 'General',
                            'Status':       row[6] if len(row)>6 else 'Present',
                        })
        except Exception as e:
            print(f"Attendance student error: {e}")

        # Get subjects list too
        subjects_list = SUBJECTS
        return render_template('attendance.html',
                               role=role,
                               name=session.get('name'),
                               students=att_records,
                               today=today,
                               selected_class='',
                               already_taken=False,
                               subjects=subjects_list,
                               classes=CLASSES,
                               class_display_map=CLASS_DISPLAY,
                               school_year=get_active_school_year())

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

    # Always pass full SUBJECTS list so all subjects appear in attendance dropdown
    # Also merge any custom subjects added via grades sheet
    subjects_list = list(SUBJECTS)
    try:
        gs = get_sheet('grades')
        if gs:
            vals = gs.get_all_values()
            from_sheet = list(dict.fromkeys([str(row[3]).strip() for row in vals[1:] if len(row)>3 and str(row[3]).strip()]))
            # Add custom subjects not in the default list
            for s in from_sheet:
                if s and s not in subjects_list:
                    subjects_list.append(s)
    except: pass

    return render_template('attendance.html',
                           role=role,
                           name=session.get('name'),
                           selected_class=selected_class,
                           students=class_students,
                           already_taken=already_taken,
                           today=today,
                           subjects=subjects_list,
                           classes=CLASSES,
                           class_display_map=CLASS_DISPLAY,
                           school_year=get_active_school_year())

@app.route('/get_subjects')
@login_required
def get_subjects():
    """Return subjects list from Google Sheet grades or fallback to SUBJECTS constant."""
    # Try to get unique subjects from grades sheet
    try:
        grades_sheet = get_sheet('grades')
        if grades_sheet:
            vals = grades_sheet.get_all_values()
            subjects_from_sheet = list(dict.fromkeys([
                str(row[3]).strip() for row in vals[1:] if len(row) > 3 and str(row[3]).strip()
            ]))
            if subjects_from_sheet:
                return jsonify({'subjects': subjects_from_sheet})
    except: pass
    return jsonify({'subjects': SUBJECTS})

@app.route('/submit_attendance', methods=['POST'])
@role_required('admin', 'attendance')
def submit_attendance():
    try:
        data            = request.get_json()
        class_          = str(data.get('class','')).strip()
        subject         = str(data.get('subject','')).strip()
        attendance_data = data.get('attendance', [])
        date_str        = str(data.get('date', '')).strip() or datetime.now().strftime('%Y-%m-%d')
        time_str        = datetime.now().strftime('%H:%M')

        if not subject:
            return jsonify({'success': False, 'message': 'Subject is required!'})

        sheet = get_sheet('attendance')
        if not sheet:
            return jsonify({'success': False, 'message': 'Attendance sheet not found!'})

        # Check if already taken for this class+subject+date
        records = sheet.get_all_records()
        existing = [r for r in records
                    if r.get('Date') == date_str
                    and str(r.get('Class','')).strip() == class_
                    and str(r.get('Subject','')).strip() == subject]
        if existing:
            return jsonify({'success': False,
                            'message': f'Attendance for {subject} on {date_str} already taken!'})

        school_year = get_active_school_year()
        rows = []
        for att in attendance_data:
            rows.append([
                date_str, time_str,
                att.get('student_id',''),
                att.get('student_name',''),
                class_, subject,
                att.get('status','Present'),
                school_year          # Col H — School_Year
            ])
        if rows:
            sheet.append_rows(rows, value_input_option='RAW')

        # Auto-update grades sheet Attendance column
        _update_attendance_in_grades(class_, subject)

        invalidate_cache('attendance')
        invalidate_cache('grades')
        return jsonify({'success': True, 'message': f'Attendance saved! {len(rows)} students.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


def _update_attendance_in_grades(class_=None, subject=None):
    """Compute attendance percentage per student per subject, write to grades sheet."""
    try:
        att_sheet    = get_sheet('attendance')
        grades_sheet = get_sheet('grades')
        if not att_sheet or not grades_sheet: return

        att_records = att_sheet.get_all_records()
        active_year = get_active_school_year()
        # Build {student_id: {subject: (present, total)}}
        att_map = {}
        for r in att_records:
            # Only count current school year
            row_year = str(r.get('School_Year','')).strip()
            if row_year and row_year != active_year: continue
            sid  = str(r.get('Student_ID','')).strip()
            subj = str(r.get('Subject','')).strip()
            if not sid or not subj: continue
            if class_ and str(r.get('Class','')).strip() != str(class_).strip(): continue
            if subject and subj != subject: continue
            key = (sid, subj)
            if key not in att_map: att_map[key] = {'present':0,'absent':0,'late':0,'total':0}
            att_map[key]['total'] += 1
            st = str(r.get('Status','')).lower()
            if st == 'present':
                att_map[key]['present'] += 1
            elif st == 'late':
                att_map[key]['late'] += 1
            else:
                att_map[key]['absent'] += 1

        if not att_map: return

        # Update grades sheet Attendance column (col index 5, 0-based = col F)
        grades_vals = grades_sheet.get_all_values()
        if not grades_vals: return
        headers = [h.strip().lower() for h in grades_vals[0]]
        # Find attendance column
        att_col = None
        for i, h in enumerate(headers):
            if 'attendance' in h: att_col = i; break

        updates = []
        for ri, row in enumerate(grades_vals[1:], start=2):
            if len(row) < 4: continue
            sid  = str(row[0]).strip()
            subj = str(row[3]).strip()
            key  = (sid, subj)
            if key in att_map:
                total_cls = att_map[key]['total']
                present   = att_map[key]['present']
                absent    = att_map[key].get('absent', total_cls - present)
                late      = att_map[key].get('late', 0)
                # Professional formula:
                # Present = full credit, Late = half credit, Absent = deducts
                # weighted_score = (present*1.0 + late*0.5) / total * 10, min 0
                if total_cls > 0:
                    weighted = (present * 1.0 + late * 0.5) / total_cls
                    att_score = round(max(weighted * 10, 0), 1)  # out of 10
                else:
                    att_score = 0
                pct = round(present / total_cls * 100, 1) if total_cls > 0 else 0
                if att_col is not None:
                    col_letter = chr(65 + att_col)
                    updates.append({'range': f'{col_letter}{ri}', 'values': [[att_score]]})

        if updates:
            grades_sheet.batch_update(updates)
    except Exception as e:
        print(f"Attendance-grades sync error: {e}")


@app.route('/get_attendance', methods=['GET'])
@login_required
def get_attendance():
    """Get attendance records for a student or class/subject."""
    try:
        student_id  = request.args.get('student_id','').strip()
        class_      = request.args.get('class','').strip()
        subject     = request.args.get('subject','').strip()
        year_filter = request.args.get('school_year','').strip()
        active_year = get_active_school_year()

        sheet = get_sheet('attendance')
        if not sheet:
            return jsonify({'records': []})

        # Try get_all_values for raw access — more reliable than get_all_records
        all_vals = sheet.get_all_values()
        result   = []
        if not all_vals or len(all_vals) < 2:
            return jsonify({'records': []})

        # Map headers to indices (case-insensitive, strip)
        raw_headers = [h.strip().lower().replace(' ','_') for h in all_vals[0]]
        def col(names):
            for n in names:
                n_low = n.strip().lower().replace(' ','_')
                if n_low in raw_headers:
                    return raw_headers.index(n_low)
            return -1

        c_date   = col(['date'])
        c_time   = col(['time'])
        c_sid    = col(['student_id','studentid','id'])
        c_name   = col(['student_name','name'])
        c_cls    = col(['class'])
        c_subj   = col(['subject'])
        c_status = col(['status'])
        c_year   = col(['school_year'])

        def safe(row, idx):
            return str(row[idx]).strip() if idx >= 0 and idx < len(row) else ''

        for i, row in enumerate(all_vals[1:], start=2):
            if not any(row): continue  # skip blank rows
            dat  = safe(row, c_date)
            tim  = safe(row, c_time) or '--'
            sid  = safe(row, c_sid)
            name = safe(row, c_name)
            cls  = safe(row, c_cls)
            subj = safe(row, c_subj)
            stat = safe(row, c_status)
            yr   = safe(row, c_year)

            # School_Year filter only if explicitly requested
            if year_filter and yr and yr != year_filter:
                continue
            # Skip completely blank data rows
            if not dat and not sid:
                continue
            if student_id and sid != student_id: continue
            if class_     and cls  != class_:    continue
            if subject    and subj != subject:   continue

            result.append({
                'row':     i,
                'date':    dat,
                'time':    tim,
                'sid':     sid,
                'name':    name,
                'class':   cls,
                'subject': subj,
                'status':  stat
            })
        return jsonify({'records': result})
    except Exception as e:
        return jsonify({'records': [], 'error': str(e)})


@app.route('/edit_attendance', methods=['POST'])
@role_required('admin', 'attendance')
def edit_attendance():
    try:
        data   = request.get_json()
        row    = int(data.get('row',0))
        status = str(data.get('status','')).strip()
        if not row or status not in ['Present','Absent','Late']:
            return jsonify({'success': False, 'message': 'Invalid data'})
        sheet = get_sheet('attendance')
        if not sheet:
            return jsonify({'success': False, 'message': 'Sheet error'})
        headers = sheet.row_values(1)
        status_col = 7  # default col G
        for i, h in enumerate(headers, start=1):
            if 'status' in h.lower(): status_col = i; break
        sheet.update_cell(row, status_col, status)
        # Re-sync attendance scores
        records = sheet.get_all_records()
        if row-2 < len(records):
            r = records[row-2]
            _update_attendance_in_grades(r.get('Class',''), r.get('Subject',''))
        invalidate_cache('attendance')
        invalidate_cache('grades')
        return jsonify({'success': True, 'message': f'Attendance updated to {status}'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/delete_attendance', methods=['POST'])
@role_required('admin', 'attendance')
def delete_attendance():
    try:
        data = request.get_json()
        row  = int(data.get('row',0))
        if not row:
            return jsonify({'success': False, 'message': 'Row required'})
        sheet = get_sheet('attendance')
        if not sheet:
            return jsonify({'success': False, 'message': 'Sheet error'})
        records = sheet.get_all_records()
        r_data  = records[row-2] if row-2 < len(records) else {}
        sheet.delete_rows(row)
        _update_attendance_in_grades(r_data.get('Class',''), r_data.get('Subject',''))
        invalidate_cache('attendance')
        invalidate_cache('grades')
        return jsonify({'success': True, 'message': 'Attendance record deleted!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# ══════════════════════════════════════
#   FEES
# ══════════════════════════════════════

# ── CONSTANTS ──
MONTHLY_FEE   = 25.0   # $25 bishii
SCHOOL_MONTHS = ['Sep','Oct','Nov','Dec','Jan','Feb','Mar','Apr','May']  # 9 bil

def get_student_fee_data(record):
    """Normalize a student record: ensure Total_Fee=25, compute status."""
    try:
        total = float(str(record.get('Total_Fee','') or '').strip() or MONTHLY_FEE)
    except (ValueError, TypeError):
        total = MONTHLY_FEE
    if total <= 0:
        total = MONTHLY_FEE

    try:
        paid = float(str(record.get('Amount_Paid','') or '').strip() or 0)
    except (ValueError, TypeError):
        paid = 0.0

    balance = round(max(0.0, total - paid), 2)
    paid    = round(paid, 2)
    total   = round(total, 2)

    if balance <= 0:
        status = 'paid'
    elif paid > 0:
        status = 'pending'
    else:
        status = 'unpaid'

    return {**record, 'Total_Fee': total, 'Amount_Paid': paid, 'Balance': balance, '_status': status}

@app.route('/fees')
@login_required
def fees():
    # school_year param for history view
    role   = session.get('role')
    search = request.args.get('search', '').lower()

    if role == 'student':
        student_id = session.get('student_id')
        records    = get_sheet_cached('students') or []
        student    = [get_student_fee_data(s) for s in records
                      if str(s.get('ID', '')) == student_id]
        return render_template('fees.html',
                               role=role,
                               name=session.get('name'),
                               students=student,
                               monthly_fee=MONTHLY_FEE,
                               school_months=SCHOOL_MONTHS,
                               search='',
                               school_year=get_active_school_year(),
                               outstanding_fees=[])

    records      = get_sheet_cached('students') or []
    all_students = [get_student_fee_data(s) for s in records
                    if s.get('ID') and str(s.get('ID', '')).startswith('CS')]
    if search:
        all_students = [s for s in all_students if
                        search in str(s.get('ID', '')).lower() or
                        search in str(s.get('Name', '')).lower()]

    active_year = get_active_school_year()
    outstanding = []
    try:
        fs_recs = get_sheet_cached('fees') or []
        if fs_recs:
            seen = set()
            for r in fs_recs:
                yr  = str(r.get('School_Year','')).strip()
                bal = float(r.get('Balance',0) or 0)
                sid = str(r.get('Student_ID','')).strip()
                key = f"{sid}_{yr}"
                if yr and yr != active_year and bal > 0 and key not in seen:
                    seen.add(key)
                    outstanding.append({'id':sid,'name':str(r.get('Student_Name','')).strip(),'year':yr,'balance':bal})
    except: pass

    return render_template('fees.html',
                           role=role,
                           name=session.get('name'),
                           students=all_students,
                           monthly_fee=MONTHLY_FEE,
                           school_months=SCHOOL_MONTHS,
                           search=search,
                           school_year=active_year,
                           outstanding_fees=outstanding)

@app.route('/pay_fee', methods=['POST'])
@role_required('admin', 'fee')
def pay_fee():
    try:
        data       = request.get_json()
        student_id = str(data.get('student_id', '')).strip()
        month      = str(data.get('month', '')).strip()  # which month this payment is for
        try:
            amount = float(data.get('amount', 0))
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'Invalid amount'})

        if amount <= 0:
            return jsonify({'success': False, 'message': 'Amount must be greater than $0'})
        if amount > MONTHLY_FEE:
            return jsonify({'success': False, 'message': f'Max ${MONTHLY_FEE:.0f} per month! Cannot pay more.'})

        # Default month to current if not provided
        if not month or month not in SCHOOL_MONTHS:
            month = datetime.now().strftime('%b')
            if month not in SCHOOL_MONTHS:
                month = SCHOOL_MONTHS[0]

        sheet = get_sheet('students')
        if not sheet:
            return jsonify({'success': False, 'message': 'Google Sheet connection error'})

        records = sheet.get_all_records()
        for i, record in enumerate(records, start=2):
            if str(record.get('ID', '')).strip() == student_id:
                fd = get_student_fee_data(record)
                current_paid = fd['Amount_Paid']
                total_fee    = fd['Total_Fee']
                balance      = fd['Balance']

                if balance <= 0:
                    return jsonify({'success': False, 'message': 'Student is already fully paid!'})

                if amount > balance:
                    return jsonify({
                        'success': False,
                        'message': f'Amount ${amount:.2f} exceeds remaining balance ${balance:.2f}!'
                    })

                new_paid    = round(current_paid + amount, 2)
                new_balance = round(max(0.0, total_fee - new_paid), 2)

                # Batch update cols F-H (Total_Fee, Amount_Paid, Balance)
                sheet.update(f'F{i}:H{i}', [[total_fee, new_paid, new_balance]])

                # SYNC monthly_fees sheet — write to the SELECTED month
                try:
                    now_str  = datetime.now().strftime('%Y-%m-%d')
                    year_str = str(datetime.now().year)
                    mf_sheet = get_monthly_sheet()
                    if mf_sheet:
                        ensure_monthly_sheet_headers(mf_sheet)
                        mf_records   = mf_sheet.get_all_records()
                        existing_row = None
                        prev_paid    = 0.0
                        for mi, mr in enumerate(mf_records, start=2):
                            if (str(mr.get('Student_ID','')).strip() == student_id and
                                    str(mr.get('Month','')).strip() == month):
                                existing_row = mi
                                prev_paid    = float(str(mr.get('Amount_Paid',0) or 0))
                                break
                        # Add to existing paid for this month
                        m_paid    = round(min(prev_paid + amount, MONTHLY_FEE), 2)
                        m_balance = round(max(0.0, MONTHLY_FEE - m_paid), 2)
                        row_data  = [
                            now_str, student_id, record.get('Name',''),
                            str(record.get('Class','')), month, year_str,
                            m_paid, m_balance, MONTHLY_FEE
                        ]
                        if existing_row:
                            mf_sheet.update(f'A{existing_row}:I{existing_row}', [row_data])
                        else:
                            mf_sheet.append_row(row_data, value_input_option='RAW')
                        invalidate_cache('monthly_fees')
                except Exception as mf_err:
                    print(f"monthly_fees sync warning: {mf_err}")

                invalidate_cache('students')
                invalidate_cache('fees')

                # Log to fees sheet
                fees_sheet = get_sheet('fees')
                if fees_sheet:
                    try:
                        fees_sheet.append_row([
                            datetime.now().strftime('%Y-%m-%d'),
                            student_id, record.get('Name',''),
                            str(record.get('Class','')),
                            total_fee, new_paid, new_balance
                        ], value_input_option='RAW')
                    except: pass

                status = 'paid' if new_balance <= 0 else ('pending' if new_paid > 0 else 'unpaid')
                return jsonify({
                    'success':     True,
                    'new_paid':    new_paid,
                    'new_balance': new_balance,
                    'total_fee':   total_fee,
                    'status':      status,
                    'message':     f'Payment ${amount:.2f} recorded successfully!'
                })

        return jsonify({'success': False, 'message': f'Student {student_id} not found'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/edit_fee', methods=['POST'])
@role_required('admin', 'fee')
def edit_fee():
    """Edit student fee record — admin can update Name, Class, Total_Fee, Amount_Paid."""
    try:
        data       = request.get_json()
        student_id = str(data.get('student_id', '')).strip()

        sheet = get_sheet('students')
        if not sheet:
            return jsonify({'success': False, 'message': 'Google Sheet connection error'})

        records = sheet.get_all_records()
        for i, record in enumerate(records, start=2):
            if str(record.get('ID', '')).strip() == student_id:

                updates = {}

                # Name (col 2)
                name = str(data.get('name', record.get('Name', ''))).strip()
                if name:
                    updates[2] = name

                # Class (col 3)
                cls = str(data.get('class', record.get('Class', ''))).strip()
                if cls:
                    updates[3] = cls

                # Total_Fee (col 6) — must be exactly MONTHLY_FEE ($25) or admin override
                try:
                    new_total = float(data.get('total_fee', MONTHLY_FEE))
                except (ValueError, TypeError):
                    new_total = MONTHLY_FEE
                updates[6] = round(new_total, 2)

                # Amount_Paid (col 7) — can be set by admin; must not exceed total_fee
                if 'amount_paid' in data:
                    try:
                        new_paid = float(data.get('amount_paid', 0))
                    except (ValueError, TypeError):
                        new_paid = 0.0
                    new_paid = round(min(new_paid, new_total), 2)
                    updates[7] = new_paid
                else:
                    try:
                        new_paid = float(str(record.get('Amount_Paid', 0) or 0))
                    except:
                        new_paid = 0.0

                new_balance = round(max(0.0, new_total - new_paid), 2)
                updates[8]  = new_balance  # col 8 = Balance

                # Batch update — single API call
                sheet.update(f'B{i}:H{i}', [[
                    updates.get(2, record.get('Name','')),
                    updates.get(3, record.get('Class','')),
                    updates.get(4, record.get('Phone','')),
                    record.get('Password',''),
                    updates.get(6, MONTHLY_FEE),
                    new_paid,
                    new_balance
                ]])

                status = 'paid' if new_balance <= 0 else ('pending' if new_paid > 0 else 'unpaid')

                # SYNC monthly_fees sheet for current month
                try:
                    cur_month = datetime.now().strftime('%b')
                    if cur_month in SCHOOL_MONTHS:
                        mf_sheet = get_monthly_sheet()
                        if mf_sheet:
                            ensure_monthly_sheet_headers(mf_sheet)
                            mf_recs  = mf_sheet.get_all_records()
                            ex_row   = None
                            for mi, mr in enumerate(mf_recs, start=2):
                                if (str(mr.get('Student_ID','')).strip()==student_id and
                                        str(mr.get('Month','')).strip()==cur_month):
                                    ex_row = mi; break
                            m_paid = round(min(new_paid, MONTHLY_FEE), 2)
                            m_bal  = round(max(0.0, MONTHLY_FEE - m_paid), 2)
                            now_s  = datetime.now().strftime('%Y-%m-%d')
                            yr_s   = str(datetime.now().year)
                            sname  = updates.get(2, record.get('Name',''))
                            scls   = updates.get(3, record.get('Class',''))
                            if ex_row:
                                mf_sheet.update(f'A{ex_row}:I{ex_row}', [[
                                    now_s, student_id, sname, scls,
                                    cur_month, yr_s, m_paid, m_bal, MONTHLY_FEE
                                ]])
                            else:
                                mf_sheet.append_row([
                                    now_s, student_id, sname, scls,
                                    cur_month, yr_s, m_paid, m_bal, MONTHLY_FEE
                                ], value_input_option='RAW')
                            invalidate_cache('monthly_fees')
                except Exception as esync:
                    print(f"edit_fee monthly sync: {esync}")

                invalidate_cache('students')
                return jsonify({
                    'success':     True,
                    'new_total':   updates[6],
                    'new_paid':    new_paid,
                    'new_balance': new_balance,
                    'status':      status,
                    'message':     'Student fee record updated!'
                })

        return jsonify({'success': False, 'message': f'Student {student_id} not found'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# ══════════════════════════════════════
#   MONTHLY FEES TRACKING
# ══════════════════════════════════════

MONTH_ORDER = {m: i for i, m in enumerate(['Sep','Oct','Nov','Dec','Jan','Feb','Mar','Apr','May'])}

def get_monthly_sheet():
    return get_sheet('monthly_fees')

def ensure_monthly_sheet_headers(sheet):
    """Make sure monthly_fees sheet has correct headers."""
    try:
        headers = sheet.row_values(1)
        expected = ['Date','Student_ID','Student_Name','Class','Month','Year','Amount_Paid','Balance','Total_Fee']
        if not headers or headers[0] != 'Date':
            sheet.insert_row(expected, 1)
    except:
        pass

@app.route('/monthly_fees')
@login_required
def monthly_fees():
    role = session.get('role')
    name = session.get('name')

    # Get all students — cached
    recs         = get_sheet_cached('students') or []
    all_students = [get_student_fee_data(s) for s in recs
                    if s.get('ID') and str(s.get('ID','')).startswith('CS')]

    # Get monthly_fees records
    mf_sheet   = get_monthly_sheet()
    mf_records = []
    if mf_sheet:
        try:
            ensure_monthly_sheet_headers(mf_sheet)
            mf_records = mf_sheet.get_all_records()
        except:
            mf_records = []

    # Build per-student monthly map: {student_id: {month: {paid, balance}}}
    monthly_map = {}
    for r in mf_records:
        sid   = str(r.get('Student_ID','')).strip()
        month = str(r.get('Month','')).strip()
        if sid and month:
            if sid not in monthly_map:
                monthly_map[sid] = {}
            monthly_map[sid][month] = {
                'paid':    float(str(r.get('Amount_Paid',0) or 0)),
                'balance': float(str(r.get('Balance',0) or 0)),
                'date':    r.get('Date',''),
            }

    # Student view — only their own
    if role == 'student':
        sid = session.get('student_id','')
        my_students = [s for s in all_students if str(s.get('ID',''))==sid]
        return render_template('monthly_fees.html',
            role=role, name=name,
            students=my_students,
            monthly_map=monthly_map,
            school_months=SCHOOL_MONTHS,
            monthly_fee=MONTHLY_FEE,
            current_year=datetime.now().year)

    active_year = get_active_school_year()
    mf_out = []
    try:
        mfs = get_sheet('monthly_fees')
        if mfs:
            seen2 = set()
            for r in mfs.get_all_records():
                yr  = str(r.get('Year','')).strip()
                bal = float(r.get('Balance',0) or 0)
                sid = str(r.get('Student_ID','')).strip()
                key = f"{sid}_{yr}"
                if yr and yr != active_year and bal > 0 and key not in seen2:
                    seen2.add(key)
                    mf_out.append({'id':sid,'name':str(r.get('Student_Name','')).strip(),'year':yr,'balance':bal})
    except: pass

    return render_template('monthly_fees.html',
        role=role, name=name,
        students=all_students,
        monthly_map=monthly_map,
        school_months=SCHOOL_MONTHS,
        monthly_fee=MONTHLY_FEE,
        current_year=datetime.now().year,
        school_year=active_year,
        outstanding_fees=mf_out)


@app.route('/pay_monthly', methods=['POST'])
@role_required('admin')
def pay_monthly():
    """Record a monthly payment for a student."""
    try:
        data       = request.get_json()
        student_id = str(data.get('student_id','')).strip()
        month      = str(data.get('month','')).strip()
        try:
            amount = float(data.get('amount', 0))
        except:
            return jsonify({'success': False, 'message': 'Invalid amount'})

        if not student_id or not month:
            return jsonify({'success': False, 'message': 'Student ID and month required'})
        if month not in SCHOOL_MONTHS:
            return jsonify({'success': False, 'message': f'Invalid month: {month}'})
        if amount <= 0:
            return jsonify({'success': False, 'message': 'Amount must be > $0'})
        if amount > MONTHLY_FEE:
            return jsonify({'success': False, 'message': f'Max ${MONTHLY_FEE:.0f} per month!'})

        # Get student info
        students_sheet = get_sheet('students')
        if not students_sheet:
            return jsonify({'success': False, 'message': 'Sheet connection error'})

        student_rec = None
        for r in students_sheet.get_all_records():
            if str(r.get('ID','')).strip() == student_id:
                student_rec = r
                break
        if not student_rec:
            return jsonify({'success': False, 'message': f'Student {student_id} not found'})

        # Check monthly_fees sheet — already paid this month?
        mf_sheet = get_monthly_sheet()
        if not mf_sheet:
            return jsonify({'success': False, 'message': 'monthly_fees sheet not found — create it in Google Sheets'})

        ensure_monthly_sheet_headers(mf_sheet)
        existing = mf_sheet.get_all_records()

        already_paid = 0.0
        existing_row = None
        for idx, r in enumerate(existing, start=2):
            if str(r.get('Student_ID','')).strip()==student_id and str(r.get('Month','')).strip()==month:
                already_paid   = float(str(r.get('Amount_Paid',0) or 0))
                existing_row   = idx
                break

        new_paid    = round(already_paid + amount, 2)
        if new_paid > MONTHLY_FEE:
            return jsonify({'success': False,
                'message': f'Total for {month} would be ${new_paid:.2f} — max is ${MONTHLY_FEE:.0f}!'})

        new_balance = round(max(0.0, MONTHLY_FEE - new_paid), 2)
        now_str     = datetime.now().strftime('%Y-%m-%d')
        year_str    = str(datetime.now().year)

        if existing_row:
            # Batch update — single API call instead of 4
            mf_sheet.update(f'A{existing_row}:I{existing_row}', [[
                now_str, student_id,
                student_rec.get('Name',''),
                str(student_rec.get('Class','')),
                month, year_str,
                new_paid, new_balance, MONTHLY_FEE
            ]])
        else:
            mf_sheet.append_row([
                now_str, student_id,
                student_rec.get('Name',''),
                str(student_rec.get('Class','')),
                month, year_str,
                new_paid, new_balance, MONTHLY_FEE
            ], value_input_option='RAW')

        # SYNC students sheet — update Amount_Paid = amount paid for THIS month
        try:
            s_sheet = get_sheet('students')
            if s_sheet:
                s_records = s_sheet.get_all_records()
                for si, sr in enumerate(s_records, start=2):
                    if str(sr.get('ID','')).strip() == student_id:
                        # Write the current month's paid amount to students sheet
                        # new_paid = what's paid for THIS month (e.g. 18)
                        # new_balance = what's left for THIS month (e.g. 7)
                        s_sheet.update(f'F{si}:H{si}',
                            [[MONTHLY_FEE, new_paid, new_balance]])
                        break
            invalidate_cache('students')
        except Exception as sync_err:
            print(f"Sync warning: {sync_err}")

        status = 'paid' if new_balance <= 0 else 'pending'
        return jsonify({
            'success':     True,
            'new_paid':    new_paid,
            'new_balance': new_balance,
            'status':      status,
            'month':       month,
            'message':     f'{month}: ${amount:.2f} recorded! Balance: ${new_balance:.2f}'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/edit_monthly', methods=['POST'])
@role_required('admin')
def edit_monthly():
    """Edit/override a monthly payment record."""
    try:
        data       = request.get_json()
        student_id = str(data.get('student_id','')).strip()
        month      = str(data.get('month','')).strip()
        try:
            new_paid = float(data.get('amount_paid', 0))
        except:
            return jsonify({'success': False, 'message': 'Invalid amount'})

        if new_paid < 0 or new_paid > MONTHLY_FEE:
            return jsonify({'success': False, 'message': f'Amount must be 0–${MONTHLY_FEE:.0f}'})

        mf_sheet = get_monthly_sheet()
        if not mf_sheet:
            return jsonify({'success': False, 'message': 'monthly_fees sheet not found'})

        ensure_monthly_sheet_headers(mf_sheet)
        records  = mf_sheet.get_all_records()
        new_bal  = round(max(0.0, MONTHLY_FEE - new_paid), 2)
        now_str  = datetime.now().strftime('%Y-%m-%d')

        for idx, r in enumerate(records, start=2):
            if str(r.get('Student_ID','')).strip()==student_id and str(r.get('Month','')).strip()==month:
                mf_sheet.update_cell(idx, 1, now_str)
                mf_sheet.update_cell(idx, 7, round(new_paid,2))
                mf_sheet.update_cell(idx, 8, new_bal)
                status = 'paid' if new_bal<=0 else ('pending' if new_paid>0 else 'unpaid')
                return jsonify({'success':True,'new_paid':new_paid,'new_balance':new_bal,'status':status,
                                'message':f'{month} updated: Paid ${new_paid:.2f}, Balance ${new_bal:.2f}'})

        # Not found — create new
        students_sheet = get_sheet('students')
        sname, scls = '', ''
        if students_sheet:
            for r in students_sheet.get_all_records():
                if str(r.get('ID','')).strip()==student_id:
                    sname = r.get('Name',''); scls = str(r.get('Class','')); break
        mf_sheet.append_row([now_str, student_id, sname, scls, month,
                              str(datetime.now().year), round(new_paid,2), new_bal, MONTHLY_FEE],
                             value_input_option='RAW')
        status = 'paid' if new_bal<=0 else ('pending' if new_paid>0 else 'unpaid')
        return jsonify({'success':True,'new_paid':new_paid,'new_balance':new_bal,'status':status,
                        'message':f'{month} record created: Paid ${new_paid:.2f}'})
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
        student_id     = session.get('student_id', '').strip()
        student_grades = {'Term1': {}, 'Term2': {}}

        # Get student info from cached students sheet
        all_stu = get_sheet_cached('students') or []
        student = {}
        for s in all_stu:
            sid = str(s.get('ID','')).strip()
            if sid == student_id:
                student = s
                break

        # Get grades — use raw values so prefix issues are caught
        try:
            sheet = get_sheet('grades')
            if sheet and student_id:
                all_values = sheet.get_all_values()
                for row in all_values[1:]:
                    if not row or len(row) < 6:
                        continue
                    # Normalize student ID — remove any leading non-alphanumeric
                    raw_id = str(row[0]).strip()
                    # Handle cases like 's401' -> 'CS401', ':401' -> 'CS401'
                    normalized = raw_id
                    if raw_id and not raw_id.upper().startswith('CS'):
                        # Try to extract digits and rebuild
                        digits = ''.join(filter(str.isdigit, raw_id))
                        if digits:
                            normalized = 'CS' + digits
                    if normalized != student_id:
                        continue
                    # Filter by active school year if col J exists
                    row_year = str(row[9]).strip() if len(row) > 9 else ''
                    if row_year and row_year != get_active_school_year():
                        continue
                    subject    = str(row[3]).strip()
                    term       = str(row[5]).strip() if len(row) > 5 else ''
                    try: score = float(row[4]) if len(row) > 4 and row[4] else 0
                    except: score = 0
                    try: bille = float(row[6]) if len(row) > 6 and row[6] else 0
                    except: bille = 0
                    try: attendance = float(row[7]) if len(row) > 7 and row[7] else 0
                    except: attendance = 0
                    # Total = score + bille + attendance (all out of their max)
                    total = round(score + bille + attendance, 1)
                    if term in student_grades and subject:
                        student_grades[term][subject] = {
                            'score':      score,
                            'bille':      bille,
                            'attendance': attendance,
                            'total':      total
                        }
        except Exception as e:
            print(f"Grades load error: {e}")

        def calc_avg(term_grades):
            totals = []
            for v in term_grades.values():
                if isinstance(v, dict):
                    t = v.get('total', 0) or v.get('score', 0)
                else:
                    try: t = float(v)
                    except: t = 0
                if t > 0: totals.append(t)
            return round(sum(totals) / len(totals), 1) if totals else 0

        t1_avg = calc_avg(student_grades['Term1'])
        t2_avg = calc_avg(student_grades['Term2'])
        final  = round((t1_avg + t2_avg) / 2, 1) if t1_avg and t2_avg else (t1_avg or t2_avg or 0)

        return render_template('grades.html',
                               role=role,
                               name=session.get('name'),
                               student=student,
                               grades=student_grades,
                               subjects=SUBJECTS,
                               t1_avg=t1_avg,
                               t2_avg=t2_avg,
                               final=final,
                               has_term1=len(student_grades['Term1']) > 0,
                               has_term2=len(student_grades['Term2']) > 0,
                               classes=CLASSES,
                               school_year=get_active_school_year())

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
                           search=search,
                           classes=CLASSES,
                           school_year=get_active_school_year())

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
            return jsonify({'success': False, 'message': 'Sheet error'})

        # DELETE existing rows for this student + term
        records = sheet.get_all_records()
        rows_to_delete = []
        for i, r in enumerate(records, start=2):
            if (str(r.get('Student_ID', '')).strip() == str(student_id).strip() and
                    str(r.get('Term', '')).strip() == str(term).strip()):
                rows_to_delete.append(i)

        # Delete from bottom to top
        for row in sorted(rows_to_delete, reverse=True):
            sheet.delete_rows(row)

        # Add new rows with Bille and Attendance columns
        # Sheet cols: Student_ID, Name, Class, Subject, Score, Term, Bille, Attendance, Date
        rows_to_add = []
        for subject, gdata in grades_data.items():
            if isinstance(gdata, dict):
                score = float(gdata.get('score', 0) or 0)
                bille = float(gdata.get('bille', 0) or 0)
            else:
                try: score = float(gdata)
                except: score = 0
                bille = 0
            rows_to_add.append([
                student_id, student_name, class_,
                subject, score, term, bille, 0, today,
                get_active_school_year()   # Col J — School_Year
            ])
        if rows_to_add:
            sheet.append_rows(rows_to_add, value_input_option='RAW')

        invalidate_cache('grades')
        return jsonify({'success': True, 'message': f'Grades saved for {len(rows_to_add)} subjects!'})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/edit_grade', methods=['POST'])
@role_required('admin', 'grades')
def edit_grade():
    """Edit a grade field — Score(col E=5), Bille(col G=7), Attendance(col H=8)."""
    try:
        data       = request.get_json()
        student_id = str(data.get('student_id','')).strip()
        subject    = str(data.get('subject','')).strip()
        term       = str(data.get('term','')).strip()
        field      = str(data.get('field','')).strip()
        try: value = float(data.get('value', 0) or 0)
        except: value = 0.0

        # Sheet column layout (1-based):
        # A=1:Student_ID, B=2:Name, C=3:Class, D=4:Subject,
        # E=5:Score, F=6:Term, G=7:Bille, H=8:Attendance, I=9:Date
        # Col: A=1=ID, B=2=Name, C=3=Class, D=4=Subject, E=5=Score,
        #      F=6=Term, G=7=Bille, H=8=Attendance, I=9=Date, J=10=School_Year
        field_col = {'score': 5, 'bille': 7, 'attendance': 8}.get(field)
        if not field_col:
            return jsonify({'success': False, 'message': f'Unknown field: {field}'})

        sheet = get_sheet('grades')
        if not sheet:
            return jsonify({'success': False, 'message': 'Grades sheet error'})

        vals = sheet.get_all_values()
        found_row = None
        for ri, row in enumerate(vals[1:], start=2):
            if len(row) < 6: continue
            rid = str(row[0]).strip()
            # Normalize: handle 's401' → 'CS401'
            if not rid.upper().startswith('CS'):
                digits = ''.join(filter(str.isdigit, rid))
                if digits: rid = 'CS' + digits
            if rid == student_id and str(row[3]).strip() == subject and str(row[5]).strip() == term:
                found_row = ri
                break

        if found_row:
            sheet.update_cell(found_row, field_col, round(value, 1))
            invalidate_cache('grades')
            return jsonify({'success': True, 'message': f'{field.title()} updated to {value}!'})

        # Row not found — create new row
        today = datetime.now().strftime('%Y-%m-%d')
        stu_records = get_sheet_cached('students') or []
        sname, scls = '', ''
        for s in stu_records:
            if str(s.get('ID','')).strip() == student_id:
                sname = s.get('Name',''); scls = str(s.get('Class','')); break
        # Col order: Student_ID, Name, Class, Subject, Score, Term, Bille, Attendance, Date
        new_row = [student_id, sname, scls, subject, 0, term, 0, 0, today]
        col_to_idx = {'score': 4, 'bille': 6, 'attendance': 7}  # 0-based index
        if field in col_to_idx: new_row[col_to_idx[field]] = round(value, 1)
        sheet.append_row(new_row, value_input_option='RAW')
        invalidate_cache('grades')
        return jsonify({'success': True, 'message': f'Grade row created with {field} = {value}!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/get_student_grades')
@login_required
def get_student_grades():
    student_id = request.args.get('student_id', '').strip()
    sheet      = get_sheet('grades')
    grades     = {'Term1': {}, 'Term2': {}}

    if sheet and student_id:
        # Use get_all_values instead of get_all_records
        all_values = sheet.get_all_values()
        if len(all_values) > 1:
            headers = [h.strip() for h in all_values[0]]
            for row in all_values[1:]:
                if not row or len(row) < 6:
                    continue
                row_id = str(row[0]).strip()
                if row_id == student_id.strip():
                    subject = str(row[3]).strip()
                    score   = row[4]
                    term    = str(row[5]).strip()
                    try:
                        score = float(score)
                    except:
                        score = 0
                    bille = row[6] if len(row) > 6 else 0
                    attendance = row[7] if len(row) > 7 else 0
                    try: bille = float(bille)
                    except: bille = 0
                    try: attendance = float(attendance)
                    except: attendance = 0
                    if term in grades and subject:
                        grades[term][subject] = {
                            'score': score, 'bille': bille, 'attendance': attendance
                        }

    return jsonify(grades)

# ══════════════════════════════════════════════════════════════════════════
#   VOTING SYSTEM (SI BUUXDA LOO MIDEEBEYEY - NO ERRORS)
# ══════════════════════════════════════════════════════════════════════════

@app.route('/votes')
@login_required
def votes():
    role = session.get('role')
    sheet         = get_sheet('candidates')
    candidates    = []
    election_open = False
    election_title = 'School Election 2026'
    election_end_time = None

    if sheet:
        try:
            records    = sheet.get_all_records()
            candidates = [c for c in records if c.get('Candidate_ID')]
            if candidates:
                status_val = str(candidates[0].get('Election_Status', 'closed')).strip().lower()
                election_open = status_val == 'open'
                # title stored in col H row 1, end_time in col I row 1
                try:
                    title_val = sheet.cell(1, 8).value
                    if title_val: election_title = title_val
                except: pass
                try:
                    et = sheet.cell(1, 9).value
                    if et: election_end_time = et
                except: pass
        except Exception as e:
            print(f"Error reading candidates sheet: {e}")

    already_voted = False
    voted_for     = None

    if role == 'student':
        student_id  = str(session.get('student_id', '')).strip()
        votes_sheet = get_sheet('votes')
        if votes_sheet and student_id:
            try:
                voters_list = [str(v).strip() for v in votes_sheet.col_values(1)]
                if student_id in voters_list:
                    already_voted = True
                    try:
                        row_index     = voters_list.index(student_id) + 1
                        voted_cand_id = str(votes_sheet.cell(row_index, 2).value).strip()
                        # Get candidate NAME instead of ID
                        voted_for = voted_cand_id  # fallback
                        cand_sheet_tmp = get_sheet('candidates')
                        if cand_sheet_tmp:
                            for cand in cand_sheet_tmp.get_all_records():
                                if str(cand.get('Candidate_ID','')).strip() == voted_cand_id:
                                    voted_for = cand.get('Name', voted_cand_id)
                                    break
                    except: voted_for = None
            except Exception as e:
                print(f"Error reading votes sheet: {e}")

    total_votes = sum(int(c.get('Votes', 0) or 0) for c in candidates)
    for c in candidates:
        vc = int(c.get('Votes', 0) or 0)
        c['percentage'] = round((vc / total_votes * 100), 1) if total_votes > 0 else 0

    sorted_candidates = sorted(candidates, key=lambda x: int(x.get('Votes', 0) or 0), reverse=True)
    winner = sorted_candidates[0] if sorted_candidates and total_votes > 0 else None

    return render_template('votes.html',
                           role=role,
                           name=session.get('name'),
                           candidates=candidates,
                           sorted_candidates=sorted_candidates,
                           election_open=election_open,
                           election_title=election_title,
                           election_end_time=election_end_time,
                           already_voted=already_voted,
                           voted_for=voted_for,
                           total_votes=total_votes,
                           winner=winner)


@app.route('/toggle_election', methods=['POST'])
@role_required('admin')
def toggle_election():
    try:
        data   = request.get_json()
        status = str(data.get('status', 'closed')).strip().lower()
        title  = str(data.get('title', '')).strip()
        timer_seconds = int(data.get('timer_seconds', 0) or 0)

        if status not in ['open', 'closed']:
            return jsonify({'success': False, 'message': 'Invalid status!'})

        sheet = get_sheet('candidates')
        if not sheet:
            return jsonify({'success': False, 'message': 'Candidates sheet not found!'})

        records = sheet.get_all_records()
        if not records and status == 'open':
            return jsonify({'success': False, 'message': 'Wax tartame ah kuma jiraan! Hubi inaad ku dartay ugu yaraan 2 tartame.'})

        if status == 'open':
            if len(records) < 2:
                return jsonify({'success': False, 'message': f'Ugu yaraan 2 tartame ayaa loo baahan yahay! Hadda waxaa jira {len(records)}.'})

            # If there is already an open election, block
            for r in records:
                if str(r.get('Election_Status', '')).lower() == 'open':
                    return jsonify({'success': False, 'message': 'Doorasho furan ayaa horaan jiray! Xir marka hore tii hore.'})

        # Update all candidates status col (col 5)
        for i in range(len(records)):
            sheet.update_cell(i + 2, 5, status)

        # Store election title and end_time in a dedicated meta sheet row (NOT candidates data rows)
        # Use a separate 'election_meta' approach: store in candidates sheet row 1 col H and I (beyond data)
        # Safe: col H(8) row 1 = title, col I(9) row 1 = end_time  (header row cols that don't affect records)
        if title:
            try: sheet.update_cell(1, 8, title)
            except: pass

        end_time_str = ''
        if status == 'open' and timer_seconds > 0:
            from datetime import timedelta
            end_dt = datetime.now() + timedelta(seconds=timer_seconds)
            end_time_str = end_dt.strftime('%Y-%m-%d %H:%M:%S')
        try: sheet.update_cell(1, 9, end_time_str)
        except: pass

        # When closing: compute winner and store in sheet
        winner_info = {}
        if status == 'closed':
            try: sheet.update_cell(1, 9, '')
            except: pass
            # Compute winner from votes
            recs_now = sheet.get_all_records()
            if recs_now:
                sorted_cands = sorted(recs_now, key=lambda x: int(x.get('Votes',0) or 0), reverse=True)
                top_votes    = int(sorted_cands[0].get('Votes',0) or 0) if sorted_cands else 0
                tied         = [x for x in sorted_cands if int(x.get('Votes',0) or 0) == top_votes and top_votes > 0]
                total_v      = sum(int(x.get('Votes',0) or 0) for x in recs_now)
                if len(tied) == 1 and top_votes > 0:
                    winner_info = {
                        'name':       tied[0].get('Name',''),
                        'id':         tied[0].get('Candidate_ID',''),
                        'votes':      top_votes,
                        'percentage': round(top_votes/total_v*100,1) if total_v>0 else 0,
                        'is_tie':     False
                    }
                elif len(tied) > 1 and top_votes > 0:
                    winner_info = {
                        'is_tie': True,
                        'tied_names': [x.get('Name','') for x in tied],
                        'votes': top_votes
                    }

        return jsonify({'success': True, 'message': f"Election {status}!",
                        'end_time': end_time_str, 'winner': winner_info})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/add_candidate', methods=['POST'])
@role_required('admin')
def add_candidate():
    try:
        candidate_id = request.form.get('candidate_id', '').strip().upper()
        name         = request.form.get('name', '').strip()
        cls          = request.form.get('class', '').strip()

        if not candidate_id or not name:
            return jsonify({'success': False, 'message': 'ID and Name required!'})

        sheet = get_sheet('candidates')
        if not sheet:
            return jsonify({'success': False, 'message': 'Candidates sheet not found!'})

        # Check duplicate
        records = sheet.get_all_records()
        for r in records:
            if str(r.get('Candidate_ID', '')).strip().upper() == candidate_id:
                return jsonify({'success': False, 'message': f'{candidate_id} is already a candidate! Laba jeer ma tartami karo.'})

        # Validate exists in students sheet
        students_sheet = get_sheet('students')
        student_name = name
        if students_sheet:
            for s in students_sheet.get_all_records():
                if str(s.get('ID', '')).strip().upper() == candidate_id:
                    student_name = s.get('Name', name)
                    if not cls: cls = str(s.get('Class', ''))
                    break

        # Max 20 candidates
        if len(records) >= 20:
            return jsonify({'success': False, 'message': 'Max 20 candidates allowed!'})

        # Save photo if provided
        photo = request.files.get('photo')
        photo_url = ''
        if photo and photo.filename:
            import os
            photo_dir = os.path.join('static', 'images', 'students')
            os.makedirs(photo_dir, exist_ok=True)
            photo_path = os.path.join(photo_dir, f'{candidate_id}.jpg')
            photo.save(photo_path)

        # Get current election status from first candidate
        current_status = 'closed'
        if records:
            current_status = str(records[0].get('Election_Status', 'closed')).lower()

        sheet.append_row([candidate_id, student_name, cls, 0, current_status], value_input_option='RAW')
        return jsonify({'success': True, 'message': f'{student_name} added as candidate!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/get_student_info', methods=['GET'])
@role_required('admin')
def get_student_info():
    """Auto-fill student info when admin types Student ID in Add Candidate form."""
    student_id = request.args.get('id', '').strip().upper()
    if not student_id:
        return jsonify({'found': False})
    sheet = get_sheet('students')
    if not sheet:
        return jsonify({'found': False, 'message': 'Sheet error'})
    for s in sheet.get_all_records():
        if str(s.get('ID', '')).strip().upper() == student_id:
            return jsonify({'found': True, 'name': s.get('Name', ''), 'class': str(s.get('Class', ''))})
    return jsonify({'found': False, 'message': f'{student_id} not found in students'})


@app.route('/update_candidate', methods=['POST'])
@role_required('admin')
def update_candidate():
    try:
        candidate_id = request.form.get('candidate_id', '').strip()
        name         = request.form.get('name', '').strip()
        cls          = request.form.get('class', '').strip()
        sheet = get_sheet('candidates')
        if not sheet:
            return jsonify({'success': False, 'message': 'Sheet error'})
        records = sheet.get_all_records()
        for i, r in enumerate(records, start=2):
            if str(r.get('Candidate_ID', '')).strip() == candidate_id:
                if name: sheet.update_cell(i, 2, name)
                if cls:  sheet.update_cell(i, 3, cls)
                photo = request.files.get('photo')
                if photo and photo.filename:
                    import os
                    photo_dir = os.path.join('static', 'images', 'students')
                    os.makedirs(photo_dir, exist_ok=True)
                    photo.save(os.path.join(photo_dir, f'{candidate_id}.jpg'))
                return jsonify({'success': True, 'message': 'Candidate updated!'})
        return jsonify({'success': False, 'message': 'Candidate not found'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/delete_candidate', methods=['POST'])
@role_required('admin')
def delete_candidate():
    try:
        data         = request.get_json()
        candidate_id = str(data.get('candidate_id', '')).strip()
        sheet = get_sheet('candidates')
        if not sheet:
            return jsonify({'success': False, 'message': 'Sheet error'})
        records = sheet.get_all_records()
        for i, r in enumerate(records, start=2):
            if str(r.get('Candidate_ID', '')).strip() == candidate_id:
                sheet.delete_rows(i)
                return jsonify({'success': True, 'message': 'Candidate deleted!'})
        return jsonify({'success': False, 'message': 'Not found'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})



@app.route('/votes_status')
@login_required
def votes_status():
    """Quick endpoint to check if election is open — for client polling."""
    try:
        sheet = get_sheet('candidates')
        if not sheet:
            return jsonify({'open': False})
        recs = sheet.get_all_records()
        is_open = any(str(r.get('Election_Status','')).lower()=='open' for r in recs)
        end_time = ''
        try: end_time = sheet.cell(1,9).value or ''
        except: pass
        return jsonify({'open': is_open, 'end_time': end_time})
    except Exception as e:
        return jsonify({'open': False, 'error': str(e)})

@app.route('/submit_vote', methods=['POST'])
@role_required('student')
def submit_vote():
    try:
        data         = request.get_json()
        candidate_id = str(data.get('candidate_id', '')).strip()
        student_id   = str(session.get('student_id', '')).strip()

        if not candidate_id or not student_id:
            return jsonify({'success': False, 'message': 'Invalid data!'})

        # Check election is open
        cand_sheet = get_sheet('candidates')
        if cand_sheet:
            recs = cand_sheet.get_all_records()
            if not recs or str(recs[0].get('Election_Status', 'closed')).lower() != 'open':
                return jsonify({'success': False, 'message': 'Election is not open!'})

        votes_sheet = get_sheet('votes')
        if not votes_sheet:
            return jsonify({'success': False, 'message': 'Votes sheet not found!'})

        # Anti-double-vote — use get_all_values (faster than col_values for small sheet)
        all_vote_rows = votes_sheet.get_all_values()
        voters_list = [str(r[0]).strip() for r in all_vote_rows[1:] if r]
        if student_id in voters_list:
            return jsonify({'success': False, 'message': 'Hore ayaad u codeysay! Hal mar kaliya ayaad codeyn kartaa.'})

        votes_sheet.append_row([student_id, candidate_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S')], value_input_option='RAW')

        # Increment candidate votes
        if cand_sheet:
            recs = cand_sheet.get_all_records()
            for i, c in enumerate(recs, start=2):
                if str(c.get('Candidate_ID', '')).strip() == candidate_id:
                    cand_sheet.update_cell(i, 4, int(c.get('Votes', 0) or 0) + 1)
                    break

        return jsonify({'success': True, 'message': 'Vote submitted! 🎉'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/reset_election', methods=['POST'])
@role_required('admin')
def reset_election():
    """Reset all votes and candidates for a new election."""
    try:
        # Clear votes sheet
        votes_sheet = get_sheet('votes')
        if votes_sheet:
            votes_sheet.clear()
            votes_sheet.append_row(['Student_ID', 'Candidate_ID', 'Date'])

        # Reset candidate votes to 0 and close election
        cand_sheet = get_sheet('candidates')
        if cand_sheet:
            records = cand_sheet.get_all_records()
            for i, r in enumerate(records, start=2):
                cand_sheet.update_cell(i, 4, 0)      # votes = 0
                cand_sheet.update_cell(i, 5, 'closed')  # status = closed
            try: cand_sheet.update_cell(2, 7, '')  # clear end_time
            except: pass

        return jsonify({'success': True, 'message': 'Election reset! All votes cleared.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# ══════════════════════════════════════
#   PROMOTE STUDENTS — NEW SCHOOL YEAR
# ══════════════════════════════════════

@app.route('/preview_promote', methods=['GET'])
@role_required('admin')
def preview_promote():
    """Return promotion preview — what will happen to each student."""
    try:
        sheet = get_sheet('students')
        grades_sheet = get_sheet('grades')
        if not sheet:
            return jsonify({'success': False, 'message': 'Sheet error'})

        school_year = get_active_school_year()
        records     = sheet.get_all_records()
        preview     = []

        # Load all grades once
        all_grades_rows = []
        if grades_sheet:
            all_grades_rows = grades_sheet.get_all_values()

        for student in records:
            student_id    = str(student.get('ID', '')).strip()
            if not student_id.startswith('CS'):
                continue
            current_class = str(student.get('Class', '')).strip()
            status        = str(student.get('Status', 'Active')).strip()
            if status == 'Graduated':
                continue

            # Calculate avg from current school year grades
            t1_scores, t2_scores = [], []
            for row in all_grades_rows[1:]:
                if not row or len(row) < 6:
                    continue
                if str(row[0]).strip() != student_id:
                    continue
                # Filter by school_year if column J exists
                row_year = str(row[9]).strip() if len(row) > 9 else ''
                if row_year and row_year != school_year:
                    continue
                term = str(row[5]).strip()
                try:
                    score = float(row[4])
                    bille = float(row[6]) if len(row) > 6 else 0
                    att   = float(row[7]) if len(row) > 7 else 0
                    total = min(score + bille + att, 100)
                    if term == 'Term1':
                        t1_scores.append(total)
                    elif term == 'Term2':
                        t2_scores.append(total)
                except:
                    pass

            t1_avg    = round(sum(t1_scores)/len(t1_scores),1) if t1_scores else 0
            t2_avg    = round(sum(t2_scores)/len(t2_scores),1) if t2_scores else 0
            final_avg = round((t1_avg+t2_avg)/2,1) if t1_avg>0 and t2_avg>0 else (t1_avg or t2_avg)

            if final_avg >= 50:
                if current_class == 'Form Four':
                    action     = 'graduate'
                    next_class = 'Graduated'
                else:
                    action     = 'promote'
                    next_class = NEXT_CLASS.get(current_class, current_class)
            else:
                action     = 'fail'
                next_class = current_class

            preview.append({
                'id':           student_id,
                'name':         student.get('Name',''),
                'current_class':current_class,
                'current_display': class_display(current_class),
                'next_class':   next_class,
                'next_display': class_display(next_class) if next_class != 'Graduated' else 'Graduated',
                'avg':          final_avg,
                'action':       action,
                't1_avg':       t1_avg,
                't2_avg':       t2_avg,
            })

        # Sort by class order
        preview.sort(key=lambda x: CLASS_ORDER.get(x['current_class'], 99))
        return jsonify({'success': True, 'preview': preview, 'school_year': school_year})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/promote_students', methods=['POST'])
@role_required('admin')
def promote_students():
    try:
        data      = request.get_json() or {}
        overrides = data.get('overrides', {})  # {student_id: 'promote'|'fail'|'graduate'}
        new_year  = data.get('new_year', '').strip()

        sheet = get_sheet('students')
        grades_sheet = get_sheet('grades')
        attendance_sheet = get_sheet('attendance')

        if not sheet:
            return jsonify({'success': False, 'message': 'Sheet error'})

        school_year = get_active_school_year()
        if new_year:
            os.environ['SCHOOL_YEAR'] = new_year

        records = sheet.get_all_records()
        results = {'promoted': [], 'failed': [], 'graduated': []}

        # Load all grades once
        all_grades_rows = []
        if grades_sheet:
            all_grades_rows = grades_sheet.get_all_values()

        # Process in REVERSE class order (Form Four first, Xaddaano last)
        indexed = [(i+2, r) for i, r in enumerate(records)]
        indexed.sort(key=lambda x: CLASS_ORDER.get(str(x[1].get('Class','')).strip(), 99), reverse=True)

        for i, student in indexed:
            student_id    = str(student.get('ID', '')).strip()
            if not student_id.startswith('CS'):
                continue
            current_class = str(student.get('Class', '')).strip()
            status        = str(student.get('Status', 'Active')).strip()
            if status == 'Graduated':
                continue

            # Calculate avg
            t1_scores, t2_scores = [], []
            for row in all_grades_rows[1:]:
                if not row or len(row) < 6:
                    continue
                if str(row[0]).strip() != student_id:
                    continue
                row_year = str(row[9]).strip() if len(row) > 9 else ''
                if row_year and row_year != school_year:
                    continue
                term = str(row[5]).strip()
                try:
                    score = float(row[4])
                    bille = float(row[6]) if len(row) > 6 else 0
                    att   = float(row[7]) if len(row) > 7 else 0
                    total = min(score + bille + att, 100)
                    if term == 'Term1':
                        t1_scores.append(total)
                    elif term == 'Term2':
                        t2_scores.append(total)
                except:
                    pass

            t1_avg    = round(sum(t1_scores)/len(t1_scores),1) if t1_scores else 0
            t2_avg    = round(sum(t2_scores)/len(t2_scores),1) if t2_scores else 0
            final_avg = round((t1_avg+t2_avg)/2,1) if t1_avg>0 and t2_avg>0 else (t1_avg or t2_avg)

            # Apply override if admin set one
            action = overrides.get(student_id, None)
            if not action:
                if final_avg >= 50:
                    action = 'graduate' if current_class == 'Form Four' else 'promote'
                else:
                    action = 'fail'

            student_name = student.get('Name', '')

            if action == 'graduate':
                sheet.update_cell(i, 10, 'Graduated')
                results['graduated'].append({'id': student_id, 'name': student_name,
                    'class': current_class, 'avg': final_avg})

            elif action == 'promote':
                next_class = NEXT_CLASS.get(current_class, current_class)
                sheet.update_cell(i, 3,  next_class)
                sheet.update_cell(i, 10, 'Active')
                results['promoted'].append({'id': student_id, 'name': student_name,
                    'from_class': class_display(current_class),
                    'to_class':   class_display(next_class), 'avg': final_avg})

            else:  # fail
                sheet.update_cell(i, 10, 'Active')
                results['failed'].append({
                    'id':    student_id,
                    'name':  student_name,
                    'class': current_class,
                    'avg':   final_avg
                })

        return jsonify({
            'success':  True,
            'results':  results,
            'message':  f"Done! {len(results['promoted'])} promoted, "
                        f"{len(results['graduated'])} graduated, "
                        f"{len(results['failed'])} failed."
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/get_promotion_status')
@login_required
def get_promotion_status():
    try:
        student_id    = session.get('student_id')
        student_class = session.get('class', '')

        sheet = get_sheet('students')
        if not sheet:
            return jsonify({'status': 'Active', 'class': student_class})

        records = sheet.get_all_records()
        for s in records:
            if str(s.get('ID', '')).strip() == str(student_id).strip():
                status = str(s.get('Status', 'Active')).strip()
                cls    = str(s.get('Class', student_class)).strip()

                # Update session
                session['class'] = cls

                return jsonify({
                    'status': status,
                    'class':  cls,
                    'name':   s.get('Name', '')
                })

        return jsonify({'status': 'Active', 'class': student_class})

    except Exception as e:
        return jsonify({'status': 'Active', 'class': student_class})


# ══════════════════════════════════════
#   ID CARDS
# ══════════════════════════════════════

def generate_qr_svg(data):
    """Generate QR code as inline SVG string."""
    if not QR_AVAILABLE:
        # Fallback: simple placeholder SVG
        return '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100"><rect width="100" height="100" fill="#162d50"/><text x="50" y="55" text-anchor="middle" fill="white" font-size="10">QR N/A</text></svg>'
    try:
        factory = qrcode.image.svg.SvgPathImage
        qr = qrcode.QRCode(
            version=2,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=4,
            border=2,
            image_factory=factory
        )
        qr.add_data(str(data))
        qr.make(fit=True)
        img = qr.make_image()
        buf = io.BytesIO()
        img.save(buf)
        svg_str = buf.getvalue().decode('utf-8')
        # Make SVG fill white for dark background
        svg_str = svg_str.replace('fill="#000000"', 'fill="#ffffff"').replace("fill='#000000'", "fill='#ffffff'")
        return svg_str
    except Exception:
        return '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100"><rect width="100" height="100" fill="#162d50"/><text x="50" y="55" text-anchor="middle" fill="white" font-size="9">QR ERROR</text></svg>'

@app.route('/id_cards')
@login_required
def id_cards():
    role = session.get('role')
    name = session.get('name')

    if role == 'student':
        student_id   = session.get('student_id')
        sheet        = get_sheet('students')
        student_data = {}
        if sheet:
            for s in sheet.get_all_records():
                if str(s.get('ID', '')) == student_id:
                    student_data = s
                    break
        qr_svg = generate_qr_svg(student_id or 'STUDENT')
        return render_template('idcard.html',
                               role=role, name=name,
                               student=student_data,
                               qr_svg=qr_svg)

    # Admin / other staff — generic QR (per-student QR generated client-side via JS)
    qr_svg = generate_qr_svg('SCHOOL-2026')
    return render_template('idcard.html',
                           role=role, name=name,
                           student={},
                           qr_svg=qr_svg)

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
