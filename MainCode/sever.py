from flask import (
    Flask, render_template_string, request, redirect, url_for,
    session, send_from_directory, send_file, flash, jsonify, abort
)
from werkzeug.utils import secure_filename
import os, io, zipfile
import logging
from waitress import serve

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# ——— Configuration ———
SERVER_FOLDER   = 'E:/server'
ACCOUNTS_FILE   = 'accounts.txt'
LIMITS_FILE     = 'limits.txt'
ADMIN_REQUESTS  = 'admin_requests.txt'
DEFAULT_LIMIT   = 1 * 1024 * 1024 * 1024  # 1 GB
ADMIN_USER      = 'admin'
ADMIN_PASS      = 'admin123'

os.makedirs(SERVER_FOLDER, exist_ok=True)

# Load accounts & limits
accounts, limits = {}, {}
for fn, tgt in [(ACCOUNTS_FILE, accounts), (LIMITS_FILE, limits)]:
    if os.path.exists(fn):
        with open(fn) as f:
            for ln in f:
                u, v = ln.strip().split(',', 1)
                tgt[u] = int(v) if fn == LIMITS_FILE else v

accounts.setdefault(ADMIN_USER, ADMIN_PASS)
limits[ADMIN_USER] = 0  # unlimited

def save_accounts():
    with open(ACCOUNTS_FILE, 'w') as f:
        for u, p in accounts.items():
            f.write(f"{u},{p}\n")

def save_limits():
    with open(LIMITS_FILE, 'w') as f:
        for u, l in limits.items():
            f.write(f"{u},{l}\n")

def get_folder_size(path):
    total = 0
    for dp, _, files in os.walk(path):
        for fn in files:
            total += os.path.getsize(os.path.join(dp, fn))
    return total

def zip_stream(paths):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in paths:
            z.write(p, os.path.basename(p))
    buf.seek(0)
    return buf

# ——— Beautiful, Animated, Responsive Templates ———
INDEX = """
<!doctype html><html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Home Cloud</title>
<style>
  :root {
    --bg:#fafafa; --card:#fff; --primary:#0066ff; --primary-hover:#0052cc;
    --text:#202124; --muted:#5f6368; --error:#d93025; --shadow:0 4px 16px rgba(0,0,0,0.1);
    --radius:12px; --gap:1rem; --transition:.3s;
  }
  *{box-sizing:border-box;margin:0;padding:0;}
  body{background:var(--bg);font-family:system-ui,sans-serif;color:var(--text);
       display:flex;align-items:center;justify-content:center;min-height:100vh;
       animation:fadeIn var(--transition) ease;}
  @keyframes fadeIn{from{opacity:0}to{opacity:1}}
  .card{background:var(--card);border-radius:var(--radius);box-shadow:var(--shadow);
        padding:2rem;max-width:360px;width:100%;text-align:center;}
  h2{margin-bottom:var(--gap);}
  input,button{width:100%;padding:.75rem;margin-bottom:var(--gap);
               border:1px solid #ccc;border-radius:var(--radius);font-size:1rem;
               transition:box-shadow var(--transition);}
  input:focus{outline:none;box-shadow:0 0 0 3px rgba(0,102,255,0.2);}
  button{background:var(--primary);color:#fff;border:none;cursor:pointer;
         position:relative;overflow:hidden;transition:background var(--transition);}
  button:hover{background:var(--primary-hover);}
  button:after{content:'';position:absolute;width:100%;height:100%;
               top:0;left:0;background:rgba(255,255,255,0.3);
               transform:scaleX(0);transform-origin:left;
               transition:transform var(--transition);}
  button:active:after{transform:scaleX(1);}
  hr{border:none;border-top:1px solid #eee;margin:var(--gap) 0;}
  .flashes{color:var(--error);list-style:none;margin-bottom:var(--gap);}
  @media(max-width:400px){.card{padding:1.5rem;}}
</style>
</head><body>
<div class="card">
  <h2>Home Cloud</h2>
  {% with msgs = get_flashed_messages() %}
    {% if msgs %}
      <ul class="flashes">{% for m in msgs %}<li>{{m}}</li>{%endfor%}</ul>
    {% endif %}
  {% endwith %}
  <form action="{{url_for('login')}}" method="post">
    <input name="username" placeholder="Username" required>
    <input name="password" type="password" placeholder="Password" required>
    <button>Log In</button>
  </form>
  <hr>
  <form action="{{url_for('signup')}}" method="post">
    <input name="username" placeholder="New Username" required>
    <input name="password" type="password" placeholder="New Password" required>
    <button>Sign Up</button>
  </form>
</div>
</body></html>
"""

DASH = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Dashboard</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha3/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body {
      background: linear-gradient(135deg, #6c63ff, #3f3d56);
      color: #fff;
      font-family: Arial, sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }
    header {
      background: #4a47a3;
      padding: 1rem 0;
      box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }
    header h1 {
      font-size: 1.5rem;
    }
    header nav a {
      color: #fff;
      text-decoration: none;
      margin-right: 1rem;
      transition: color 0.3s ease;
    }
    header nav a:hover {
      color: #00c4ff;
    }
    .container {
      flex: 1;
      padding: 2rem;
      animation: fadeIn 1s ease;
    }
    .storage {
      background: #fff;
      color: #333;
      border-radius: 12px;
      padding: 1.5rem;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
      margin-bottom: 2rem;
      animation: slideIn 1s ease;
    }
    .progress-bar-container {
      background: #e9ecef;
      border-radius: 12px;
      overflow: hidden;
      height: 20px;
    }
    .progress-bar {
      background: #6c63ff;
      height: 100%;
      transition: width 0.5s ease;
    }
    .actions {
      display: flex;
      gap: 1rem;
      flex-wrap: wrap;
    }
    .actions button, .actions label {
      background: #6c63ff;
      color: #fff;
      border: none;
      padding: 0.75rem 1.5rem;
      border-radius: 8px;
      cursor: pointer;
      transition: background 0.3s ease, transform 0.2s ease;
    }
    .actions button:hover, .actions label:hover {
      background: #5a54d1;
      transform: translateY(-2px);
    }
    .dragdrop {
      border: 2px dashed #fff;
      padding: 2rem;
      text-align: center;
      border-radius: 12px;
      color: #fff;
      margin-bottom: 2rem;
      animation: pulse 2s infinite;
    }
    .files {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;
    }
    .file-card {
      background: #fff;
      color: #333;
      border-radius: 12px;
      padding: 1rem;
      box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
      animation: fadeIn 1s ease;
    }
    @keyframes fadeIn {
      from {
        opacity: 0;
        transform: translateY(20px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }
    @keyframes slideIn {
      from {
        opacity: 0;
        transform: translateX(-50px);
      }
      to {
        opacity: 1;
        transform: translateX(0);
      }
    }
    @keyframes pulse {
      0%, 100% {
        opacity: 1;
      }
      50% {
        opacity: 0.7;
      }
    }
  </style>
</head>
<body>
<header>
  <div class="container d-flex justify-content-between align-items-center">
    <h1>Home Cloud</h1>
    <nav>
      <a href="{{ url_for('pricing') }}" class="text-white me-3">Pricing</a>
      <a href="{{ url_for('file_manager') }}" class="text-white me-3">File Manager</a>
      <a href="{{ url_for('logout') }}" class="text-white">Sign Out</a>
    </nav>
  </div>
</header>
<div class="container">
  <div class="storage">
    <h2>Storage Usage</h2>
    <div class="progress-bar-container">
      <div class="progress-bar" style="width: {{ (used_bytes / limit_bytes) * 100 }}%;"></div>
    </div>
    <p class="mt-2 text-center">
      <strong>{{ (used_bytes/1024/1024)|round(2) }} MB</strong> / 
      {{ (limit_bytes/1024/1024)|round(2) }} MB
    </p>
  </div>
  <div class="actions">
    <form action="{{ url_for('upload') }}" method="post" enctype="multipart/form-data">
      <label for="fileElem" class="btn btn-primary">📤 Upload File</label>
      <input type="file" id="fileElem" name="file" style="display: none;" onchange="this.form.submit()">
    </form>
    <button onclick="requestUpgrade()">🆙 Request More</button>
  </div>
  <div class="dragdrop" id="dropzone">Drag &amp; Drop files here</div>
  <div class="files" id="fileList">
    <!-- File cards will be dynamically rendered here -->
  </div>
</div>
<script>
  // JavaScript for file handling omitted for brevity
</script>
</body>
</html>
"""

ADMIN = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Admin Dashboard</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha3/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body {
      background: linear-gradient(135deg, #6c63ff, #3f3d56);
      color: #fff;
      font-family: Arial, sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }
    header {
      background: #4a47a3;
      padding: 1rem 0;
      box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }
    header h1 {
      font-size: 1.5rem;
    }
    header nav a {
      color: #fff;
      text-decoration: none;
      margin-right: 1rem;
      transition: color 0.3s ease;
    }
    header nav a:hover {
      color: #00c4ff;
    }
    .container {
      flex: 1;
      padding: 2rem;
      animation: fadeIn 1s ease;
    }
    .admin-header {
      text-align: center;
      margin-bottom: 2rem;
    }
    .user-card {
      background: #fff;
      color: #333;
      border-radius: 12px;
      padding: 1.5rem;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
      transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    .user-card:hover {
      transform: translateY(-5px);
      box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
    }
    .user-card h5 {
      font-size: 1.25rem;
      margin-bottom: 1rem;
    }
    .user-card p {
      margin-bottom: 0.5rem;
    }
    .user-card .btn {
      margin-top: 1rem;
      transition: background 0.3s ease, transform 0.2s ease;
    }
    .user-card .btn:hover {
      background: #5a54d1;
      transform: translateY(-2px);
    }
    .pending-requests {
      margin-top: 3rem;
    }
    @keyframes fadeIn {
      from {
        opacity: 0;
        transform: translateY(20px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }
    /* Responsive Design */
    @media (max-width: 768px) {
      .user-card {
        padding: 1rem;
      }
      .user-card h5 {
        font-size: 1rem;
      }
      .user-card p {
        font-size: 0.9rem;
      }
      .user-card .btn {
        font-size: 0.8rem;
        padding: 0.5rem 1rem;
      }
    }
    @media (max-width: 576px) {
      .admin-header h1 {
        font-size: 1.5rem;
      }
      .admin-header p {
        font-size: 1rem;
      }
    }
  </style>
</head>
<body>
  <header>
    <div class="container d-flex justify-content-between align-items-center">
      <h1>Admin Dashboard</h1>
      <a href="{{ url_for('logout') }}" class="text-white">Sign Out</a>
    </div>
  </header>

  <div class="container">
    <div class="admin-header">
      <h1 class="display-4">Admin Dashboard</h1>
      <p class="lead">Manage users and their storage.</p>
    </div>

    <h2>Users</h2>
    <div class="row g-4">
      {% for user, data in users.items() %}
      <div class="col-lg-4 col-md-6 col-sm-12">
        <div class="user-card">
          <h5>{{ user }}</h5>
          <p>Used: {{ (data.used / 1024 / 1024) | round(2) }} MB</p>
          <p>Limit: {{ (data.limit / 1024 / 1024 / 1024) | round(2) }} GB</p>

          <!-- Update Storage Form -->
          <form action="{{ url_for('update_storage', username=user) }}" method="post" style="display:inline;">
            <label for="new_limit_{{ user }}">New Limit (GB):</label>
            <input type="number" name="new_limit" id="new_limit_{{ user }}" min="1" max="10" step="1" value="{{ (data.limit / 1024 / 1024 / 1024) | round(0) }}" required>
            <button class="btn btn-warning">Update Storage</button>
          </form>

          <!-- Reset Password Form -->
          <form action="{{ url_for('reset_password', username=user) }}" method="post" style="display:inline;">
            <input type="text" name="new_password" placeholder="New Password" required>
            <button class="btn btn-secondary">Reset Password</button>
          </form>

          <!-- Delete Account Form -->
          <form action="{{ url_for('delete_account', username=user) }}" method="post" style="display:inline;">
            <button class="btn btn-danger">Delete Account</button>
          </form>
        </div>
      </div>
      {% endfor %}
    </div>

    <div class="pending-requests">
      <h2>Pending Requests</h2>
      <ul>
        {% for req in reqs %}
        <li>{{ req }}</li>
        {% endfor %}
      </ul>
    </div>
  </div>

  <footer class="bg-dark text-white text-center py-3">
    <p>&copy; 2025 Home Cloud. All rights reserved.</p>
  </footer>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

PRICING = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Pricing Plans</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha3/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body {
      background-color: #f8f9fa;
      font-family: Arial, sans-serif;
    }
    .pricing-header {
      text-align: center;
      margin-bottom: 2rem;
    }
    .pricing-card {
      border: 1px solid #ddd;
      border-radius: 8px;
      padding: 1.5rem;
      background-color: #fff;
      box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
      transition: transform 0.3s ease;
    }
    .pricing-card:hover {
      transform: translateY(-5px);
    }
    .pricing-card h2 {
      font-size: 1.5rem;
      margin-bottom: 1rem;
    }
    .pricing-card p {
      margin-bottom: 0.5rem;
    }
    .pricing-card .btn {
      margin-top: 1rem;
    }
  </style>
</head>
<body>
  <header class="bg-primary text-white py-3">
    <div class="container d-flex justify-content-between align-items-center">
      <h1 class="h3">Home Cloud</h1>
      <nav>
        <a href="{{ url_for('dashboard') }}" class="text-white me-3">Dashboard</a>
        <a href="{{ url_for('logout') }}" class="text-white">Sign Out</a>
      </nav>
    </div>
  </header>

  <div class="container my-5">
    <div class="pricing-header">
      <h1 class="display-4">Pricing Plans</h1>
      <p class="lead">Choose the plan that best suits your needs.</p>
    </div>
    <div class="row g-4">
      <div class="col-md-3">
        <div class="pricing-card text-center">
          <h2>Free/Forever</h2>
          <p>Storage: 1GB</p>
          <p>Price: <strong>Free</strong></p>
          <button class="btn btn-outline-primary">Select</button>
        </div>
      </div>
      <div class="col-md-3">
        <div class="pricing-card text-center">
          <h2>Basic</h2>
          <p>Storage: 2GB</p>
          <p>Price: <strong>$1.12/month</strong></p>
          <button class="btn btn-primary">Select</button>
        </div>
      </div>
      <div class="col-md-3">
        <div class="pricing-card text-center">
          <h2>Pro</h2>
          <p>Storage: 3GB</p>
          <p>Price: <strong>$2.24/month</strong></p>
          <button class="btn btn-primary">Select</button>
        </div>
      </div>
      <div class="col-md-3">
        <div class="pricing-card text-center">
          <h2>Enterprise</h2>
          <p>Storage: 4GB</p>
          <p>Price: <strong>$4.50/month</strong></p>
          <button class="btn btn-primary">Select</button>
        </div>
      </div>
    </div>
  </div>

  <footer class="bg-dark text-white text-center py-3">
    <p>&copy; 2025 Home Cloud. All rights reserved.</p>
  </footer>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

FILE_MANAGER = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>File Manager</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha3/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body {
      background-color: #f8f9fa;
      font-family: Arial, sans-serif;
    }
    .file-manager-header {
      text-align: center;
      margin-bottom: 2rem;
    }
    .file-card {
      border: 1px solid #ddd;
      border-radius: 8px;
      padding: 1rem;
      background-color: #fff;
      box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
      transition: transform 0.3s ease;
    }
    .file-card:hover {
      transform: translateY(-5px);
    }
    .file-card .btn {
      margin-top: 1rem;
    }
    .file-actions {
      display: flex;
      justify-content: center;
      gap: 0.5rem;
    }
  </style>
</head>
<body>
  <header class="bg-primary text-white py-3">
    <div class="container d-flex justify-content-between align-items-center">
      <h1 class="h3">File Manager</h1>
      <nav>
        <a href="{{ url_for('dashboard') }}" class="text-white me-3">Dashboard</a>
        <a href="{{ url_for('pricing') }}" class="text-white me-3">Pricing</a>
        <a href="{{ url_for('logout') }}" class="text-white">Sign Out</a>
      </nav>
    </div>
  </header>

  <div class="container my-5">
    <div class="file-manager-header">
      <h1 class="display-4">Your Files</h1>
      <p class="lead">Manage your files below.</p>
    </div>
    <div class="row g-4">
      {% for file in files %}
      <div class="col-lg-3 col-md-4 col-sm-6 col-12">
        <div class="file-card text-center">
          <h5>{{ file }}</h5>
          <div class="file-actions">
            <a href="{{ url_for('download', fn=file) }}" class="btn btn-success">Download</a>
            <form action="{{ url_for('delete') }}" method="post" style="display:inline;">
              <input type="hidden" name="file" value="{{ file }}">
              <button type="submit" class="btn btn-danger">Delete</button>
            </form>
          </div>
        </div>
      </div>
      {% endfor %}
    </div>
  </div>

  <footer class="bg-dark text-white text-center py-3">
    <p>&copy; 2025 Home Cloud. All rights reserved.</p>
  </footer>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""


# ——— Routes ———
@app.route('/')
def index():
    if session.get('is_admin'): return redirect(url_for('admin'))
    if 'username' in session: return redirect(url_for('dashboard'))
    return render_template_string(INDEX)

@app.route('/login', methods=['POST'])
def login():
    u, p = request.form['username'], request.form['password']
    if u == ADMIN_USER and p == ADMIN_PASS:
        session.clear(); session['username'] = u; session['is_admin'] = True
        return redirect(url_for('admin'))
    if u in accounts and accounts[u] == p:
        session.clear(); session['username'] = u; session['is_admin'] = False
        return redirect(url_for('dashboard'))
    flash('Invalid credentials'); return redirect(url_for('index'))

@app.route('/signup', methods=['POST'])
def signup():
    u, p = request.form['username'], request.form['password']
    if u in accounts or u == ADMIN_USER:
        flash('Username exists')
    else:
        accounts[u] = p
        limits[u] = DEFAULT_LIMIT
        save_accounts()
        save_limits()
        user_folder = os.path.join(SERVER_FOLDER, u)
        os.makedirs(user_folder, exist_ok=True)  # Ensure the user's directory is created
        session.clear()
        session['username'] = u
        session['is_admin'] = False
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if session.get('is_admin'): return redirect(url_for('admin'))
    if 'username' not in session: return redirect(url_for('index'))
    used = get_folder_size(os.path.join(SERVER_FOLDER, session['username']))
    limit = limits.get(session['username'], DEFAULT_LIMIT)
    return render_template_string(DASH, used_bytes=used, limit_bytes=limit)

@app.route('/status')
def status():
    if 'username' not in session or session.get('is_admin'): abort(403)
    base = os.path.join(SERVER_FOLDER, session['username'])
    return jsonify({
        "used": get_folder_size(base),
        "limit": limits.get(session['username'], DEFAULT_LIMIT),
        "files": os.listdir(base)
    })

@app.route('/upload', methods=['POST'])
def upload():
    if 'username' not in session or session.get('is_admin'):
        abort(403)
    
    base = os.path.join(SERVER_FOLDER, session['username'])
    os.makedirs(base, exist_ok=True)  # Ensure the user's folder exists

    f = request.files.get('file')
    if not f or f.filename == '':
        flash('No file selected for upload!')
        return redirect(url_for('dashboard'))

    fn = secure_filename(f.filename)
    dest = os.path.join(base, fn)

    try:
        f.save(dest)
        # Check if the storage limit is exceeded
        if limits[session['username']] and get_folder_size(base) > limits[session['username']]:
            os.remove(dest)
            flash('Storage limit exceeded! File not uploaded.')
        else:
            flash('File uploaded successfully!')
    except Exception as e:
        flash(f'Error uploading file: {str(e)}')

    return redirect(url_for('dashboard'))

@app.route('/download')
def download():
    if 'username' not in session or session.get('is_admin'): abort(403)
    fn = request.args.get('fn','')
    return send_from_directory(os.path.join(SERVER_FOLDER, session['username']), fn, as_attachment=True)

@app.route('/download_bulk')
def download_bulk():
    if 'username' not in session or session.get('is_admin'): abort(403)
    fns = request.args.get('fns','').split(',')
    paths = [os.path.join(SERVER_FOLDER, session['username'], fn) for fn in fns if fn]
    buf = zip_stream(paths)
    return send_file(buf, mimetype='application/zip',
                     as_attachment=True, download_name='files.zip')

@app.route('/delete', methods=['POST'])
def delete():
    if 'username' not in session or session.get('is_admin'):
        abort(403)
    
    base = os.path.join(SERVER_FOLDER, session['username'])
    
    # Debugging: Log the request data
    print("Request data:", request.form)
    
    # Handle both JSON and form-data
    if request.is_json:
        data = request.get_json()
        files = data.get('files', [])
    else:
        files = [request.form.get('file')]

    for fn in files:
        if fn:  # Ensure the filename is not empty
            file_path = os.path.join(base, fn)
            if os.path.exists(file_path):
                os.remove(file_path)
    
    return ('', 204)

@app.route('/request_upgrade', methods=['POST'])
def request_upgrade():
    if 'username' not in session or session.get('is_admin'): abort(403)
    with open(ADMIN_REQUESTS, 'a') as f: f.write(f"{session['username']}\n")
    return ('', 204)

@app.route('/admin')
def admin():
    if not session.get('is_admin'):
        return redirect(url_for('index'))
    
    # Load user data
    users = {}
    for user, limit in limits.items():
        user_folder = os.path.join(SERVER_FOLDER, user)
        used_storage = get_folder_size(user_folder) if os.path.exists(user_folder) else 0
        users[user] = {
            'limit': limit,
            'used': used_storage
        }
    
    # Load pending requests
    reqs = []
    if os.path.exists(ADMIN_REQUESTS):
        with open(ADMIN_REQUESTS) as f:
            reqs = sorted({ln.strip() for ln in f if ln.strip() != ADMIN_USER})
    
    return render_template_string(ADMIN, users=users, reqs=reqs)

@app.route('/approve/<username>', methods=['POST'])
def approve(username):
    if not session.get('is_admin'): abort(403)
    prev = limits.get(username, DEFAULT_LIMIT)
    limits[username] = prev + DEFAULT_LIMIT
    save_limits()
    if os.path.exists(ADMIN_REQUESTS):
        with open(ADMIN_REQUESTS) as f:
            lines = [ln for ln in f if ln.strip() != username]
        with open(ADMIN_REQUESTS, 'w') as f: f.writelines(lines)
    flash(f'Granted +1 GB to {username}')
    return redirect(url_for('admin'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/pricing')
def pricing():
    return render_template_string(PRICING)

@app.route('/file_manager')
def file_manager():
    if 'username' not in session or session.get('is_admin'): 
        return redirect(url_for('index'))
    user_folder = os.path.join(SERVER_FOLDER, session['username'])
    files = os.listdir(user_folder)
    return render_template_string(FILE_MANAGER, files=files)

@app.route('/delete_user_files/<username>', methods=['POST'])
def delete_user_files(username):
    if not session.get('is_admin'):
        abort(403)
    user_folder = os.path.join(SERVER_FOLDER, username)
    for root, dirs, files in os.walk(user_folder):
        for file in files:
            os.remove(os.path.join(root, file))
    flash(f"All files for user {username} have been deleted.")
    return redirect(url_for('admin'))

@app.route('/grant_storage/<username>', methods=['POST'])
def grant_storage(username):
    if not session.get('is_admin'):
        abort(403)
    limits[username] = limits.get(username, DEFAULT_LIMIT) + DEFAULT_LIMIT
    save_limits()
    flash(f"Granted +1 GB to {username}.")
    return redirect(url_for('admin'))

@app.route('/update_storage/<username>', methods=['POST'])
def update_storage(username):
    if not session.get('is_admin'):
        abort(403)
    try:
        new_limit_gb = float(request.form.get('new_limit'))  # Convert to float first
        new_limit_bytes = int(new_limit_gb * 1024 * 1024 * 1024)  # Convert GB to bytes
        limits[username] = new_limit_bytes
        save_limits()
        flash(f"Updated storage limit for {username} to {new_limit_gb} GB.")
    except ValueError:
        flash("Invalid storage limit value. Please enter a valid number.")
    return redirect(url_for('admin'))

@app.route('/reset_password/<username>', methods=['POST'])
def reset_password(username):
    if not session.get('is_admin'):
        abort(403)
    new_password = request.form.get('new_password')
    if not new_password:
        flash('Password cannot be empty.')
        return redirect(url_for('admin'))
    accounts[username] = new_password
    save_accounts()
    flash(f"Password for {username} has been reset.")
    return redirect(url_for('admin'))

@app.route('/delete_account/<username>', methods=['POST'])
def delete_account(username):
    if not session.get('is_admin'):
        abort(403)
    # Remove user from accounts and limits
    accounts.pop(username, None)
    limits.pop(username, None)
    save_accounts()
    save_limits()

    # Delete user's files
    user_folder = os.path.join(SERVER_FOLDER, username)
    if os.path.exists(user_folder):
        for root, dirs, files in os.walk(user_folder):
            for file in files:
                os.remove(os.path.join(root, file))
        os.rmdir(user_folder)

    flash(f"Account for {username} has been deleted.")
    return redirect(url_for('admin'))

if __name__ == '__main__':
    save_accounts()
    save_limits()

    # Configure Flask logging
    logging.basicConfig(level=logging.DEBUG)  # Set logging level to DEBUG for detailed logs
    werkzeug_logger = logging.getLogger('werkzeug')  # Get Flask's built-in logger
    werkzeug_logger.setLevel(logging.DEBUG)  # Set Flask's logger to DEBUG level

    # Print server startup messages
    print("Scanning Database...")
    print("Server is running on http://0.0.0.0:5000")
    print("DDNS Starting Using Flask...")

    # Use Flask's built-in development server
    app.run(host='0.0.0.0', port=5000, debug=True)