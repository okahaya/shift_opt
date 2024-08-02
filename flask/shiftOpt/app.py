from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import re
import importlib.util
# from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.secret_key = 'your_secret_key'
# socketio = SocketIO(app)

# 外部スクリプトをインポート
spec = importlib.util.spec_from_file_location("make_shift", "make_shift.py")
make_shift = importlib.util.module_from_spec(spec)
spec.loader.exec_module(make_shift)

# データベースの初期化
def init_db():
    with sqlite3.connect('shift_scheduler.db') as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                password TEXT,
                owner TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS shifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER,
                shift_name TEXT,
                start_time INTEGER,
                end_time INTEGER,
                required_workers INTEGER,
                FOREIGN KEY (event_id) REFERENCES events(id)
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS workers (
                name TEXT,
                unavailable_times TEXT,
                event_id INTEGER,
                FOREIGN KEY (event_id) REFERENCES events(id)
            )
        ''')
        conn.commit()

init_db()

def user_exists(username):
    with sqlite3.connect('shift_scheduler.db') as conn:
        c = conn.cursor()
        c.execute('SELECT 1 FROM users WHERE username = ?', (username,))
        return c.fetchone() is not None

def save_user(username, password):
    if user_exists(username):
        raise sqlite3.IntegrityError("このユーザー名は既に使用されています。")
    with sqlite3.connect('shift_scheduler.db') as conn:
        c = conn.cursor()
        c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
        conn.commit()

def authenticate_user(username, password):
    with sqlite3.connect('shift_scheduler.db') as conn:
        c = conn.cursor()
        c.execute('SELECT 1 FROM users WHERE username = ? AND password = ?', (username, password))
        return c.fetchone() is not None

def validate_time_format(time_str):
    pattern = r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$'
    return bool(re.match(pattern, time_str))

def time_to_minutes(time_str):
    hours, minutes = map(int, time_str.split(':'))
    return hours * 60 + minutes

def minutes_to_time(minutes):
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02}:{mins:02}"


def save_worker_availability(event_id, name, unavailable_times):
    with sqlite3.connect('shift_scheduler.db') as conn:
        c = conn.cursor()
        c.execute('INSERT INTO workers (name, unavailable_times, event_id) VALUES (?, ?, ?)', (name, str(unavailable_times), event_id))
        conn.commit()

def get_all_workers(event_id):
    with sqlite3.connect('shift_scheduler.db') as conn:
        c = conn.cursor()
        c.execute('SELECT name, unavailable_times FROM workers WHERE event_id = ?', (event_id,))
        rows = c.fetchall()
        return [{'name': row[0], 'unavailable_times': eval(row[1])} for row in rows]

def save_shift(event_id, shift_name, start_time, end_time, required_workers):
    with sqlite3.connect('shift_scheduler.db') as conn:
        c = conn.cursor()
        c.execute('INSERT INTO shifts (event_id, shift_name, start_time, end_time, required_workers) VALUES (?, ?, ?, ?, ?)',
                  (event_id, shift_name, start_time, end_time, required_workers))
        conn.commit()

def get_all_shifts(event_id):
    with sqlite3.connect('shift_scheduler.db') as conn:
        c = conn.cursor()
        c.execute('SELECT id, shift_name, start_time, end_time, required_workers FROM shifts WHERE event_id = ?', (event_id,))
        rows = c.fetchall()
        return [{'id': row[0], 'shift_name': row[1], 'start_time': minutes_to_time(row[2]), 'end_time': minutes_to_time(row[3]), 'required_workers': row[4]} for row in rows]

def delete_shift(shift_id):
    with sqlite3.connect('shift_scheduler.db') as conn:
        c = conn.cursor()
        c.execute('DELETE FROM shifts WHERE id = ?', (shift_id,))
        conn.commit()

def update_worker_availability(name, unavailable_times):
    with sqlite3.connect('shift_scheduler.db') as conn:
        c = conn.cursor()
        c.execute('UPDATE workers SET unavailable_times = ? WHERE name = ?', (str(unavailable_times), name))
        conn.commit()

def delete_worker_availability(name):
    with sqlite3.connect('shift_scheduler.db') as conn:
        c = conn.cursor()
        c.execute('DELETE FROM workers WHERE name = ?', (name,))
        conn.commit()

@app.route('/delete_shift/<int:shift_id>', methods=['POST'])
def delete_shift(shift_id):
    if 'username' not in session or 'event_id' not in session:
        return redirect(url_for('login'))

    event_id = session['event_id']

    with sqlite3.connect('shift_scheduler.db') as conn:
        c = conn.cursor()
        c.execute('DELETE FROM shifts WHERE id = ? AND event_id = ?', (shift_id, event_id))
        conn.commit()

    return redirect(url_for('owner'))


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if authenticate_user(username, password):
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            error = "ユーザー名またはパスワードが間違っています。"
            return render_template('login.html', error=error)
    return render_template('login.html')

@app.route('/create_event', methods=['GET', 'POST'])
def create_event():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        event_name = request.form['event_name']
        event_password = request.form['event_password']
        owner = session['username']

        with sqlite3.connect('shift_scheduler.db') as conn:
            c = conn.cursor()
            c.execute('INSERT INTO events (name, password, owner) VALUES (?, ?, ?)', (event_name, event_password, owner))
            conn.commit()
            event_id = c.lastrowid
        
        session['event_id'] = event_id
        return redirect(url_for('owner'))
    
    return render_template('create_event.html')


@app.route('/join_event', methods=['GET', 'POST'])
def join_event():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        event_name = request.form['event_name']
        event_password = request.form['event_password']
        
        with sqlite3.connect('shift_scheduler.db') as conn:
            c = conn.cursor()
            c.execute('SELECT id FROM events WHERE name = ? AND password = ?', (event_name, event_password))
            event = c.fetchone()
            if event:
                session['event_id'] = event[0]
                return redirect(url_for('worker'))
            else:
                return render_template('join_event.html', error="イベント名またはパスワードが間違っています。")
    
    return render_template('join_event.html')


@app.route('/delete_event/<int:event_id>', methods=['POST'])
def delete_event(event_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']

    with sqlite3.connect('shift_scheduler.db') as conn:
        c = conn.cursor()
        c.execute('SELECT owner FROM events WHERE id = ?', (event_id,))
        event = c.fetchone()
        if event and event[0] == username:
            c.execute('DELETE FROM shifts WHERE event_id = ?', (event_id,))
            c.execute('DELETE FROM workers WHERE event_id = ?', (event_id,))
            c.execute('DELETE FROM events WHERE id = ?', (event_id,))
            conn.commit()

    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']

    with sqlite3.connect('shift_scheduler.db') as conn:
        c = conn.cursor()
        c.execute('SELECT id, name FROM events WHERE owner = ?', (username,))
        owned_events = c.fetchall()

    return render_template('dashboard.html', owned_events=owned_events)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            save_user(username, password)
            success = "登録が完了しました。ログインしてください。"
            return render_template('login.html', success=success)
        except sqlite3.IntegrityError as e:
            error = str(e)
            return render_template('register.html', error=error)
    return render_template('register.html')

@app.route('/join_event_as_owner/<int:event_id>')
def join_event_as_owner(event_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    session['event_id'] = event_id
    return redirect(url_for('owner'))

@app.route('/owner', methods=['GET', 'POST'])
def owner():
    if 'username' not in session or 'event_id' not in session:
        return redirect(url_for('login'))
    
    event_id = session['event_id']
    error = request.args.get('error')
    success = None

    if request.method == 'POST':
        if request.form['action'] == 'add_shift':
            shift_name = request.form['shift_name']
            start_time = request.form['start_time']
            end_time = request.form['end_time']
            required_workers = request.form['required_workers']

            if validate_time_format(start_time) and validate_time_format(end_time):
                start_time_minutes = time_to_minutes(start_time)
                end_time_minutes = time_to_minutes(end_time)
                save_shift(event_id, shift_name, start_time_minutes, end_time_minutes, int(required_workers))
                success = "シフトが追加されました。"
            else:
                error = "時間は半角で XX:YY のフォーマットで入力してください。"

        elif request.form['action'] == 'bulk_add_shift':
            interval_start_time = request.form['interval_start_time']
            interval_end_time = request.form['interval_end_time']
            shift_duration = int(request.form['shift_duration'])
            interval = int(request.form['interval'])
            shift_name = request.form['bulk_shift_name']
            required_workers = int(request.form['bulk_required_workers'])

            if validate_time_format(interval_start_time) and validate_time_format(interval_end_time):
                interval_start_minutes = time_to_minutes(interval_start_time)
                interval_end_minutes = time_to_minutes(interval_end_time)
                current_start = interval_start_minutes
                while current_start + shift_duration <= interval_end_minutes:
                    save_shift(event_id, shift_name, current_start, current_start + shift_duration, required_workers)
                    current_start += shift_duration + interval
                success = "時間枠が一括登録されました。"
            else:
                error = "開始時刻と終了時刻は半角で XX:YY のフォーマットで入力してください。"

    shifts = get_all_shifts(event_id)
    workers = get_all_workers(event_id)

    return render_template('owner.html', shifts=shifts, workers=workers, error=error, success=success)


@app.route('/worker', methods=['GET', 'POST'])
def worker():
    if 'username' not in session or 'event_id' not in session:
        return redirect(url_for('login'))

    event_id = session['event_id']
    error = None
    success = None

    if request.method == 'POST':
        name = session['username']
        start_times = request.form.getlist('start_time')
        end_times = request.form.getlist('end_time')

        unavailable_times = []

        for start_time, end_time in zip(start_times, end_times):
            if validate_time_format(start_time) and validate_time_format(end_time):
                start_time_minutes = time_to_minutes(start_time)
                end_time_minutes = time_to_minutes(end_time)
                unavailable_times.append((start_time_minutes, end_time_minutes))
            else:
                error = "時間は半角で XX:YY のフォーマットで入力してください。"
                break

        if not error:
            save_worker_availability(event_id, name, unavailable_times)
            success = "都合の悪い時間が登録されました。"

    workers = get_all_workers(event_id)
    user_unavailable_times = next((worker['unavailable_times'] for worker in workers if worker['name'] == session['username']), [])
    return render_template('worker.html', workers=workers, user_unavailable_times=user_unavailable_times, error=error, success=success)

@app.route('/update_availability', methods=['POST'])
def update_availability():
    name = session['username']
    start_time = request.form['start_time']
    end_time = request.form['end_time']

    if validate_time_format(start_time) and validate_time_format(end_time):
        start_time_minutes = time_to_minutes(start_time)
        end_time_minutes = time_to_minutes(end_time)
        unavailable_times = [(start_time_minutes, end_time_minutes)]
        update_worker_availability(name, unavailable_times)
        return redirect(url_for('worker'))
    else:
        error = "時間は半角で XX:YY のフォーマットで入力してください。"
        return render_template('worker.html', error=error)
    
@app.route('/delete_availability', methods=['POST'])
def delete_availability():
    name = session['username']
    delete_worker_availability(name)
    return redirect(url_for('worker'))

@app.route('/delete_shift/<int:shift_id>', methods=['POST'])
def delete_shift_route(shift_id):
    delete_shift(shift_id)
    return redirect(url_for('owner'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))
  
@app.route('/create_shifts', methods=['POST'])
def create_shifts():
    if 'username' not in session or 'event_id' not in session:
        return redirect(url_for('login'))

    event_id = session['event_id']
    workers = get_all_workers(event_id)
    shifts = get_all_shifts(event_id)

    unique_shifts = list(set(shift['shift_name'] for shift in shifts))

    member_dict = {worker['name']: worker['unavailable_times'] for worker in workers}
    jobs = unique_shifts
    time_schedules = []
    requireds = []

    for job in jobs:
        job_time_schedules = []
        job_requireds = []
        for shift in shifts:
            if shift['shift_name'] == job:
                job_time_schedules.append((time_to_minutes(shift['start_time']), time_to_minutes(shift['end_time'])))
                job_requireds.append(shift['required_workers'])
        time_schedules.append(job_time_schedules)
        requireds.append(job_requireds)

    time_allowance = 5
    result = make_shift.create_shift(member_dict, jobs, time_schedules, requireds, time_allowance)

    if result == -1:
        return redirect(url_for('owner', error='シフト作成に失敗しました。人数や条件を再度確認してください。'))

    session['initial_schedule_result'] = result
    session['initial_jobs'] = jobs
    session['initial_time_schedules'] = time_schedules
    session['schedule_result'] = result
    session['jobs'] = jobs
    session['time_schedules'] = time_schedules

    return redirect(url_for('shift_result'))        

@app.route('/shift_result')
def shift_result():
    if 'username' not in session:
        return redirect(url_for('login'))

    schedule_result = session.get('schedule_result')

    jobs = session.get('jobs')
    time_schedules = session.get('time_schedules')
    if not schedule_result or not jobs or not time_schedules:
        return redirect(url_for('owner'))

    worker_dict = {}
    for i, job in enumerate(schedule_result):
        for j, time_slot in enumerate(job):
            for worker in time_slot:
                if worker not in worker_dict:
                    worker_dict[worker] = []
                worker_dict[worker].append((jobs[i], minutes_to_time(time_schedules[i][j][0]), minutes_to_time(time_schedules[i][j][1])))

    return render_template('shift_result.html', schedule_result=schedule_result, jobs=jobs, time_schedules=time_schedules,worker_dict=worker_dict)

@app.route('/reset_edits', methods=['POST'])
def reset_edits():
    try:
        if 'initial_schedule_result' in session and 'initial_jobs' in session and 'initial_time_schedules' in session:
            session['schedule_result'] = session['initial_schedule_result']
            session['jobs'] = session['initial_jobs']
            session['time_schedules'] = session['initial_time_schedules']
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'failure', 'reason': str(e)})


# sample_data.pyを読み込む
spec = importlib.util.spec_from_file_location("sample_data", "sample_data.py")
sample_data = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sample_data)


@app.route('/insert_sample_data', methods=['POST'])
def insert_sample_data():
    if 'username' not in session:
        return redirect(url_for('login'))

    event_name = request.form['event_name']

    with sqlite3.connect('shift_scheduler.db') as conn:
        c = conn.cursor()

        c.execute('SELECT id FROM events WHERE name = ?', (event_name,))
        event = c.fetchone()
        if not event:
            return redirect(url_for('dashboard', error="指定されたイベント名が存在しません。"))

        event_id = event[0]

        sample_shifts = [(event_id, shift_name, start_time, end_time, required_workers) for _, shift_name, start_time, end_time, required_workers in sample_data.shifts]
        c.executemany('INSERT INTO shifts (event_id, shift_name, start_time, end_time, required_workers) VALUES (?, ?, ?, ?, ?)', sample_shifts)

        sample_workers = [(name, str(unavailable_times), event_id) for name, unavailable_times, _ in sample_data.workers]
        c.executemany('INSERT INTO workers (name, unavailable_times, event_id) VALUES (?, ?, ?)', sample_workers)

        conn.commit()

    return redirect(url_for('dashboard'))



if __name__ == '__main__':
    app.jinja_env.globals.update(minutes_to_time=minutes_to_time)
    app.jinja_env.globals.update(enumerate=enumerate)
    app.run(debug=True)