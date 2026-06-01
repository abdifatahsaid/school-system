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
                    session['class'] = str(s.get('Class', ''))
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
            datetime.now().strftime('%Y-%m-%d'),
            'Active'
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

                sheet.update_cell(i, 2, name)
                sheet.update_cell(i, 3, class_)
                sheet.update_cell(i, 4, phone)
                sheet.update_cell(i, 6, total_fee)
                sheet.update_cell(i, 8, new_balance)
                if enrollment_date:
                    sheet.update_cell(i, 9, enrollment_date)

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
    role   = session.get('role')
    search = request.args.get('search', '').lower()

    if role == 'student':
        student_id = session.get('student_id')
        sheet      = get_sheet('students')
        student    = []
        if sheet:
            records = sheet.get_all_records()
            student = [get_student_fee_data(s) for s in records
                       if str(s.get('ID', '')) == student_id]
        return render_template('fees.html',
                               role=role,
                               name=session.get('name'),
                               students=student,
                               monthly_fee=MONTHLY_FEE,
                               school_months=SCHOOL_MONTHS,
                               search='')

    sheet        = get_sheet('students')
    all_students = []
    if sheet:
        records      = sheet.get_all_records()
        all_students = [get_student_fee_data(s) for s in records
                        if s.get('ID') and str(s.get('ID', '')).startswith('CS')]
        if search:
            all_students = [s for s in all_students if
                            search in str(s.get('ID', '')).lower() or
                            search in str(s.get('Name', '')).lower()]

    return render_template('fees.html',
                           role=role,
                           name=session.get('name'),
                           students=all_students,
                           monthly_fee=MONTHLY_FEE,
                           school_months=SCHOOL_MONTHS,
                           search=search)

@app.route('/pay_fee', methods=['POST'])
@role_required('admin', 'fee')
def pay_fee():
    try:
        data       = request.get_json()
        student_id = str(data.get('student_id', '')).strip()
        try:
            amount = float(data.get('amount', 0))
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'Invalid amount'})

        if amount <= 0:
            return jsonify({'success': False, 'message': 'Amount must be greater than $0'})
        if amount > MONTHLY_FEE:
            return jsonify({'success': False, 'message': f'Max ${MONTHLY_FEE:.0f} per month! Cannot pay more.'})

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

                # Col7=Amount_Paid, Col8=Balance
                sheet.update_cell(i, 7, new_paid)
                sheet.update_cell(i, 8, new_balance)
                # Ensure Total_Fee = 25 is written if it was missing
                if fd['Total_Fee'] != float(str(record.get('Total_Fee','') or 0) or 0):
                    sheet.update_cell(i, 6, total_fee)

                # Log to fees sheet
                fees_sheet = get_sheet('fees')
                if fees_sheet:
                    fees_sheet.append_row([
                        datetime.now().strftime('%Y-%m-%d'),
                        student_id,
                        record.get('Name', ''),
                        str(record.get('Class', '')),
                        total_fee,
                        new_paid,
                        new_balance
                    ], value_input_option='RAW')

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

                # Write all updates
                for col, val in updates.items():
                    sheet.update_cell(i, col, val)

                status = 'paid' if new_balance <= 0 else ('pending' if new_paid > 0 else 'unpaid')
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

    # Get all students
    students_sheet = get_sheet('students')
    all_students   = []
    if students_sheet:
        recs = students_sheet.get_all_records()
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

    return render_template('monthly_fees.html',
        role=role, name=name,
        students=all_students,
        monthly_map=monthly_map,
        school_months=SCHOOL_MONTHS,
        monthly_fee=MONTHLY_FEE,
        current_year=datetime.now().year)


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
            # Update existing row
            mf_sheet.update_cell(existing_row, 5,  month)
            mf_sheet.update_cell(existing_row, 7,  new_paid)
            mf_sheet.update_cell(existing_row, 8,  new_balance)
            mf_sheet.update_cell(existing_row, 1,  now_str)
        else:
            mf_sheet.append_row([
                now_str, student_id,
                student_rec.get('Name',''),
                str(student_rec.get('Class','')),
                month, year_str,
                new_paid, new_balance, MONTHLY_FEE
            ], value_input_option='RAW')

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
        sheet          = get_sheet('grades')
        student_grades = {'Term1': {}, 'Term2': {}}

        if sheet and student_id:
            # Use get_all_values — more reliable
            all_values = sheet.get_all_values()
            if len(all_values) > 1:
                for row in all_values[1:]:
                    if not row or len(row) < 6:
                        continue
                    row_id = str(row[0]).strip()
                    if row_id == student_id:
                        subject = str(row[3]).strip()
                        score   = row[4]
                        term    = str(row[5]).strip()
                        try:
                            score = float(score)
                        except:
                            score = 0
                        if term in student_grades and subject:
                            student_grades[term][subject] = score

        def calc_avg(term_grades):
            scores = [float(v) for v in term_grades.values()
                      if v != '' and v is not None]
            return round(sum(scores) / len(scores), 1) if scores else 0

        t1_avg = calc_avg(student_grades['Term1'])
        t2_avg = calc_avg(student_grades['Term2'])

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

        # Add new rows
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
                    if term in grades and subject:
                        grades[term][subject] = score

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
                # title may be stored in a meta row or a separate cell — try col F row 1
                try:
                    title_val = sheet.cell(1, 6).value
                    if title_val: election_title = title_val
                except: pass
                # end_time stored in col G row 2
                try:
                    et = sheet.cell(2, 7).value
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
                        row_index = voters_list.index(student_id) + 1
                        voted_for = str(votes_sheet.cell(row_index, 2).value).strip()
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

        # Store election title in col F row 1 (header row — use a safe cell)
        if title:
            try: sheet.update_cell(1, 6, title)
            except: pass

        # Store end_time in col G row 2
        end_time_str = ''
        if status == 'open' and timer_seconds > 0:
            from datetime import timedelta
            end_dt = datetime.now() + timedelta(seconds=timer_seconds)
            end_time_str = end_dt.strftime('%Y-%m-%d %H:%M:%S')
        try: sheet.update_cell(2, 7, end_time_str)
        except: pass

        # When closing: reset voted status for students (clear votes sheet? No — just close)
        if status == 'closed':
            # Clear end time
            try: sheet.update_cell(2, 7, '')
            except: pass

        return jsonify({'success': True, 'message': f"Election {status}!", 'end_time': end_time_str})
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

        # Anti-double-vote
        voters_list = [str(v).strip() for v in votes_sheet.col_values(1)]
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

@app.route('/promote_students', methods=['POST'])
@role_required('admin')
def promote_students():
    try:
        sheet = get_sheet('students')
        grades_sheet = get_sheet('grades')

        if not sheet:
            return jsonify({'success': False, 'message': 'Sheet error'})

        records = sheet.get_all_records()
        results = {
            'promoted': [],
            'failed':   [],
            'graduated': []
        }

        for i, student in enumerate(records, start=2):
            student_id = str(student.get('ID', '')).strip()
            if not student_id.startswith('CS'):
                continue

            current_class = str(student.get('Class', '')).strip()
            status        = str(student.get('Status', 'Active')).strip()

            # Already graduated skip
            if status == 'Graduated':
                continue

            # Get grades
            t1_scores = []
            t2_scores = []

            if grades_sheet:
                all_grades = grades_sheet.get_all_values()
                if len(all_grades) > 1:
                    for row in all_grades[1:]:
                        if not row or len(row) < 6:
                            continue
                        if str(row[0]).strip() == student_id:
                            term = str(row[5]).strip()
                            try:
                                score = float(row[4])
                                if term == 'Term1':
                                    t1_scores.append(score)
                                elif term == 'Term2':
                                    t2_scores.append(score)
                            except:
                                pass

            # Calculate averages
            t1_avg = round(sum(t1_scores) / len(t1_scores), 1) if t1_scores else 0
            t2_avg = round(sum(t2_scores) / len(t2_scores), 1) if t2_scores else 0

            # Final average
            if t1_avg > 0 and t2_avg > 0:
                final_avg = round((t1_avg + t2_avg) / 2, 1)
            elif t1_avg > 0:
                final_avg = t1_avg
            else:
                final_avg = 0

            student_name = student.get('Name', '')

            # Promotion decision
            if final_avg >= 50:
                if current_class == '4':
                    # Graduate
                    sheet.update_cell(i, 10, 'Graduated')
                    results['graduated'].append({
                        'id':    student_id,
                        'name':  student_name,
                        'class': current_class,
                        'avg':   final_avg
                    })
                else:
                    # Promote to next class
                    next_class = str(int(current_class) + 1)
                    sheet.update_cell(i, 3,  next_class)
                    sheet.update_cell(i, 10, 'Active')
                    results['promoted'].append({
                        'id':         student_id,
                        'name':       student_name,
                        'from_class': current_class,
                        'to_class':   next_class,
                        'avg':        final_avg
                    })
            else:
                # Failed — stay same class
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
#   ID CARDS ROUTES — app.py ku dar
#   Meesha ku dar: # ══ ANNOUNCEMENT ══ KA HOR
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
