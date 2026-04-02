import os
import json
import secrets
from datetime import datetime, timedelta, date
from functools import wraps
from io import BytesIO
import base64

from flask import (Flask, render_template_string, request, redirect, url_for,
                   flash, session, jsonify, send_file, make_response)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         login_required, current_user)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# ============================================================
# APP CONFIGURATION
# ============================================================
app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(32)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///temple_management.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'devotees'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'samaya'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'mandapam'), exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ============================================================
# DATABASE MODELS
# ============================================================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(150))
    role = db.Column(db.String(20), default='user')  # admin, user
    is_active_user = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class PoojaType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ExpenseType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Devotee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    dob = db.Column(db.Date)
    relation_type = db.Column(db.String(50))
    mobile_no = db.Column(db.String(20))
    whatsapp_no = db.Column(db.String(20))
    wedding_day = db.Column(db.Date)
    natchathiram = db.Column(db.String(100))
    address = db.Column(db.Text)
    photo_filename = db.Column(db.String(300))
    is_family_head = db.Column(db.Boolean, default=True)
    family_head_id = db.Column(db.Integer, db.ForeignKey('devotee.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    family_members = db.relationship('Devotee', backref=db.backref('family_head_ref', remote_side=[id]),
                                     lazy='dynamic')
    yearly_poojas = db.relationship('DevoteeYearlyPooja', backref='devotee', lazy='dynamic',
                                    cascade='all, delete-orphan')


class DevoteeYearlyPooja(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    devotee_id = db.Column(db.Integer, db.ForeignKey('devotee.id'), nullable=False)
    pooja_type_id = db.Column(db.Integer, db.ForeignKey('pooja_type.id'))
    pooja_name = db.Column(db.String(200))
    pooja_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Bill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bill_number = db.Column(db.String(50))
    manual_bill_no = db.Column(db.String(50))
    bill_book_no = db.Column(db.String(50))
    bill_date = db.Column(db.DateTime, default=datetime.utcnow)
    devotee_type = db.Column(db.String(20))  # enrolled, guest
    devotee_id = db.Column(db.Integer, db.ForeignKey('devotee.id'), nullable=True)
    guest_name = db.Column(db.String(200))
    guest_address = db.Column(db.Text)
    guest_mobile = db.Column(db.String(20))
    guest_whatsapp = db.Column(db.String(20))
    pooja_type_id = db.Column(db.Integer, db.ForeignKey('pooja_type.id'))
    amount = db.Column(db.Float, default=0.0)
    notes = db.Column(db.Text)
    is_deleted = db.Column(db.Boolean, default=False)
    deleted_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    devotee = db.relationship('Devotee', backref='bills')
    pooja_type = db.relationship('PoojaType', backref='bills')


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    expense_type_id = db.Column(db.Integer, db.ForeignKey('expense_type.id'))
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    expense_date = db.Column(db.Date, default=date.today)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    expense_type = db.relationship('ExpenseType', backref='expenses')


class SamayaVakuppu(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(200), nullable=False)
    dob = db.Column(db.Date)
    address = db.Column(db.Text)
    father_mother_name = db.Column(db.String(200))
    bond_issue_date = db.Column(db.Date)
    bond_scan_filename = db.Column(db.String(300))
    photo_filename = db.Column(db.String(300))
    bond_issuing_bank = db.Column(db.String(200))
    branch_of_bank = db.Column(db.String(200))
    bond_no = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ThirumanaMandapam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.Text)
    bond_no = db.Column(db.String(100))
    bond_issued_date = db.Column(db.Date)
    amount = db.Column(db.Float, default=0.0)
    no_of_bond = db.Column(db.Integer, default=1)
    bond_scan_filename = db.Column(db.String(300))
    photo_filename = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class DailyPooja(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pooja_name = db.Column(db.String(200), nullable=False)
    pooja_time = db.Column(db.String(50))
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)


# ============================================================
# LOGIN MANAGER
# ============================================================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Admin access required!', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# ============================================================
# NATCHATHIRAM LIST
# ============================================================
NATCHATHIRAM_LIST = [
    'அசுவினி (Ashwini)', 'பரணி (Bharani)', 'கார்த்திகை (Krittika)',
    'ரோகிணி (Rohini)', 'மிருகசீரிடம் (Mrigashira)', 'திருவாதிரை (Ardra)',
    'புனர்பூசம் (Punarvasu)', 'பூசம் (Pushya)', 'ஆயில்யம் (Ashlesha)',
    'மகம் (Magha)', 'பூரம் (Purva Phalguni)', 'உத்திரம் (Uttara Phalguni)',
    'ஹஸ்தம் (Hasta)', 'சித்திரை (Chitra)', 'சுவாதி (Swati)',
    'விசாகம் (Vishakha)', 'அனுஷம் (Anuradha)', 'கேட்டை (Jyeshtha)',
    'மூலம் (Mula)', 'பூராடம் (Purva Ashadha)', 'உத்திராடம் (Uttara Ashadha)',
    'திருவோணம் (Shravana)', 'அவிட்டம் (Dhanishta)', 'சதயம் (Shatabhisha)',
    'பூரட்டாதி (Purva Bhadrapada)', 'உத்திரட்டாதி (Uttara Bhadrapada)',
    'ரேவதி (Revati)'
]

RELATION_TYPES = [
    'Self', 'Spouse', 'Son', 'Daughter', 'Father', 'Mother',
    'Brother', 'Sister', 'Grandfather', 'Grandmother',
    'Father-in-law', 'Mother-in-law', 'Son-in-law', 'Daughter-in-law',
    'Uncle', 'Aunt', 'Nephew', 'Niece', 'Cousin', 'Other'
]


# ============================================================
# MAIN HTML TEMPLATE
# ============================================================

MAIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🕉️ Temple Management System</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <link href="https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css" rel="stylesheet">
    <style>
        :root {
            --temple-primary: #ff6600;
            --temple-secondary: #cc3300;
            --temple-gold: #FFD700;
            --temple-dark: #8B0000;
            --temple-light: #FFF8DC;
            --temple-green: #228B22;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #FFF8DC 0%, #FFEFD5 50%, #FFE4B5 100%);
            min-height: 100vh;
        }

        /* Sidebar */
        .sidebar {
            position: fixed;
            top: 0;
            left: 0;
            width: 260px;
            height: 100vh;
            background: linear-gradient(180deg, #8B0000 0%, #B22222 50%, #DC143C 100%);
            color: white;
            z-index: 1000;
            overflow-y: auto;
            transition: all 0.3s;
            box-shadow: 4px 0 15px rgba(0,0,0,0.3);
        }

        .sidebar-header {
            padding: 20px 15px;
            text-align: center;
            border-bottom: 2px solid rgba(255,215,0,0.3);
            background: rgba(0,0,0,0.2);
        }

        .sidebar-header h3 {
            color: #FFD700;
            font-size: 1.1em;
            margin-top: 8px;
        }

        .sidebar-header .temple-icon {
            font-size: 2.5em;
            color: #FFD700;
        }

        .sidebar-menu {
            padding: 10px 0;
        }

        .sidebar-menu a {
            display: flex;
            align-items: center;
            padding: 12px 20px;
            color: #FFF8DC;
            text-decoration: none;
            transition: all 0.3s;
            border-left: 3px solid transparent;
            font-size: 0.95em;
        }

        .sidebar-menu a:hover, .sidebar-menu a.active {
            background: rgba(255,215,0,0.15);
            border-left: 3px solid #FFD700;
            color: #FFD700;
        }

        .sidebar-menu a i {
            width: 30px;
            text-align: center;
            margin-right: 10px;
            font-size: 1.1em;
        }

        .sidebar-menu .menu-divider {
            border-top: 1px solid rgba(255,215,0,0.2);
            margin: 8px 20px;
        }

        /* Main Content */
        .main-content {
            margin-left: 260px;
            padding: 20px;
            min-height: 100vh;
        }

        /* Top Bar */
        .top-bar {
            background: white;
            border-radius: 12px;
            padding: 15px 25px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        /* News Ticker */
        .news-ticker-container {
            background: linear-gradient(90deg, #8B0000, #DC143C, #8B0000);
            border-radius: 10px;
            padding: 10px 15px;
            margin-bottom: 20px;
            overflow: hidden;
            position: relative;
        }

        .news-ticker {
            display: flex;
            animation: ticker 30s linear infinite;
            white-space: nowrap;
        }

        .news-ticker span {
            color: #FFD700;
            padding: 0 50px;
            font-weight: 500;
            font-size: 1em;
        }

        @keyframes ticker {
            0% { transform: translateX(100%); }
            100% { transform: translateX(-100%); }
        }

        /* Dashboard Cards */
        .stat-card {
            border-radius: 15px;
            padding: 25px;
            color: white;
            box-shadow: 0 5px 20px rgba(0,0,0,0.15);
            transition: transform 0.3s;
            position: relative;
            overflow: hidden;
        }

        .stat-card:hover {
            transform: translateY(-5px);
        }

        .stat-card::after {
            content: '';
            position: absolute;
            top: -50%;
            right: -50%;
            width: 100%;
            height: 100%;
            background: rgba(255,255,255,0.05);
            border-radius: 50%;
        }

        .stat-card.income { background: linear-gradient(135deg, #228B22, #32CD32); }
        .stat-card.expense { background: linear-gradient(135deg, #DC143C, #FF4500); }
        .stat-card.devotees { background: linear-gradient(135deg, #4169E1, #6495ED); }
        .stat-card.bills { background: linear-gradient(135deg, #FF8C00, #FFD700); }

        .stat-card h6 { font-size: 0.85em; opacity: 0.9; margin-bottom: 5px; }
        .stat-card h3 { font-size: 1.8em; font-weight: 700; }
        .stat-card .stat-icon { font-size: 3em; opacity: 0.3; position: absolute; right: 20px; top: 20px; }

        /* Cards */
        .content-card {
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 15px rgba(0,0,0,0.08);
            padding: 25px;
            margin-bottom: 20px;
        }

        .content-card h5 {
            color: #8B0000;
            border-bottom: 2px solid #FFD700;
            padding-bottom: 10px;
            margin-bottom: 20px;
            font-weight: 600;
        }

        /* Buttons */
        .btn-temple {
            background: linear-gradient(135deg, #8B0000, #DC143C);
            color: white;
            border: none;
            padding: 10px 25px;
            border-radius: 8px;
            font-weight: 500;
            transition: all 0.3s;
        }

        .btn-temple:hover {
            background: linear-gradient(135deg, #DC143C, #FF4500);
            color: white;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(220,20,60,0.4);
        }

        .btn-gold {
            background: linear-gradient(135deg, #DAA520, #FFD700);
            color: #8B0000;
            border: none;
            padding: 10px 25px;
            border-radius: 8px;
            font-weight: 600;
        }

        .btn-gold:hover {
            background: linear-gradient(135deg, #FFD700, #FFA500);
            color: #8B0000;
        }

        /* Form Controls */
        .form-control:focus, .form-select:focus {
            border-color: #DC143C;
            box-shadow: 0 0 0 0.2rem rgba(220,20,60,0.25);
        }

        .form-label {
            font-weight: 600;
            color: #555;
            font-size: 0.9em;
        }

        /* Table */
        .table thead {
            background: linear-gradient(135deg, #8B0000, #DC143C);
            color: white;
        }

        .table thead th {
            font-weight: 600;
            border: none;
            padding: 12px;
        }

        /* Daily Pooja Card */
        .pooja-card {
            background: linear-gradient(135deg, #FFF8DC, #FFEFD5);
            border: 1px solid #FFD700;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 10px;
            border-left: 4px solid #8B0000;
        }

        .pooja-time {
            color: #8B0000;
            font-weight: 700;
        }

        /* Period Buttons */
        .period-btn {
            border: 2px solid #8B0000;
            color: #8B0000;
            background: white;
            padding: 8px 20px;
            border-radius: 25px;
            font-weight: 600;
            margin: 0 3px;
            transition: all 0.3s;
        }

        .period-btn:hover, .period-btn.active {
            background: #8B0000;
            color: #FFD700;
        }

        /* Photo preview */
        .photo-preview {
            width: 100px;
            height: 100px;
            border-radius: 50%;
            object-fit: cover;
            border: 3px solid #FFD700;
        }

        /* Responsive */
        @media (max-width: 768px) {
            .sidebar { width: 0; overflow: hidden; }
            .sidebar.show { width: 260px; }
            .main-content { margin-left: 0; }
        }

        .tab-selector .nav-link {
            color: #8B0000;
            font-weight: 600;
        }
        .tab-selector .nav-link.active {
            background: #8B0000;
            color: #FFD700;
        }

        /* Login Page */
        .login-container {
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #8B0000 0%, #DC143C 50%, #FF4500 100%);
        }

        .login-card {
            background: white;
            border-radius: 20px;
            padding: 40px;
            width: 400px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }

        .family-member-card {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 10px;
            position: relative;
        }

        .yearly-pooja-entry {
            background: #FFF8DC;
            border: 1px solid #FFD700;
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 8px;
        }

        .badge-temple {
            background: #8B0000;
            color: #FFD700;
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 0.8em;
        }

        /* Print styles */
        @media print {
            .sidebar, .top-bar, .no-print { display: none !important; }
            .main-content { margin-left: 0 !important; }
        }
    </style>
</head>
<body>
{% if current_user.is_authenticated %}
<!-- SIDEBAR -->
<div class="sidebar" id="sidebar">
    <div class="sidebar-header">
        <div class="temple-icon">🕉️</div>
        <h3>Temple Management</h3>
        <small style="color: #FFD700; opacity: 0.7;">{{ current_user.full_name or current_user.username }}</small>
    </div>
    <div class="sidebar-menu">
        <a href="{{ url_for('dashboard') }}" class="{% if request.endpoint == 'dashboard' %}active{% endif %}">
            <i class="fas fa-tachometer-alt"></i> Dashboard
        </a>
        <a href="{{ url_for('devotees') }}" class="{% if request.endpoint in ['devotees','add_devotee','edit_devotee','view_devotee'] %}active{% endif %}">
            <i class="fas fa-users"></i> Devotees
        </a>
        <a href="{{ url_for('billing') }}" class="{% if request.endpoint in ['billing','new_bill','view_bill'] %}active{% endif %}">
            <i class="fas fa-file-invoice"></i> Billing
        </a>
        <a href="{{ url_for('expenses_page') }}" class="{% if request.endpoint == 'expenses_page' %}active{% endif %}">
            <i class="fas fa-money-bill-wave"></i> Expenses
        </a>
        <a href="{{ url_for('reports') }}" class="{% if request.endpoint == 'reports' %}active{% endif %}">
            <i class="fas fa-chart-bar"></i> Reports
        </a>
        <div class="menu-divider"></div>
        <a href="{{ url_for('samaya_vakuppu') }}" class="{% if request.endpoint in ['samaya_vakuppu','add_samaya','edit_samaya'] %}active{% endif %}">
            <i class="fas fa-graduation-cap"></i> Samaya Vakuppu
        </a>
        <a href="{{ url_for('thirumana_mandapam') }}" class="{% if request.endpoint in ['thirumana_mandapam','add_mandapam','edit_mandapam'] %}active{% endif %}">
            <i class="fas fa-building"></i> Thirumana Mandapam
        </a>
        <div class="menu-divider"></div>
        <a href="{{ url_for('daily_pooja_page') }}" class="{% if request.endpoint == 'daily_pooja_page' %}active{% endif %}">
            <i class="fas fa-om"></i> Daily Pooja
        </a>
        <a href="{{ url_for('settings') }}" class="{% if request.endpoint == 'settings' %}active{% endif %}">
            <i class="fas fa-cog"></i> Settings
        </a>
        {% if current_user.role == 'admin' %}
        <a href="{{ url_for('user_management') }}" class="{% if request.endpoint == 'user_management' %}active{% endif %}">
            <i class="fas fa-user-shield"></i> User Management
        </a>
        {% endif %}
        <div class="menu-divider"></div>
        <a href="{{ url_for('logout') }}">
            <i class="fas fa-sign-out-alt"></i> Logout
        </a>
    </div>
</div>

<!-- MAIN CONTENT -->
<div class="main-content">
    <div class="top-bar">
        <div>
            <button class="btn btn-sm btn-outline-danger d-md-none" onclick="document.getElementById('sidebar').classList.toggle('show')">
                <i class="fas fa-bars"></i>
            </button>
            <span style="color: #8B0000; font-weight: 600;">
                <i class="fas fa-om"></i> {{ page_title|default('Dashboard') }}
            </span>
        </div>
        <div>
            <span class="text-muted"><i class="fas fa-calendar"></i> {{ now().strftime('%d %B %Y, %A') }}</span>
        </div>
    </div>

    <!-- Flash Messages -->
    {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
    {% for category, message in messages %}
    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
        {{ message }}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    </div>
    {% endfor %}
    {% endif %}
    {% endwith %}

    {% block content %}{% endblock %}
</div>
{% else %}
{% block login_content %}{% endblock %}
{% endif %}

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
<script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
<script src="https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js"></script>
<script>
$(document).ready(function() {
    if ($.fn.DataTable) {
        $('.data-table').DataTable({
            pageLength: 10,
            responsive: true,
            order: [[0, 'desc']]
        });
    }
});
</script>
{% block extra_js %}{% endblock %}
</body>
</html>
"""

# ============================================================
# PAGE TEMPLATES
# ============================================================

LOGIN_TEMPLATE = """
{% extends "main" %}
{% block login_content %}
<div class="login-container">
    <div class="login-card">
        <div class="text-center mb-4">
            <div style="font-size: 3em;">🕉️</div>
            <h4 style="color: #8B0000; font-weight: 700;">Temple Management</h4>
            <p class="text-muted">Please login to continue</p>
        </div>
        {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
        {% for category, message in messages %}
        <div class="alert alert-{{ category }} py-2">{{ message }}</div>
        {% endfor %}
        {% endif %}
        {% endwith %}
        <form method="POST">
            <div class="mb-3">
                <label class="form-label">Username</label>
                <div class="input-group">
                    <span class="input-group-text"><i class="fas fa-user"></i></span>
                    <input type="text" name="username" class="form-control" required placeholder="Enter username">
                </div>
            </div>
            <div class="mb-3">
                <label class="form-label">Password</label>
                <div class="input-group">
                    <span class="input-group-text"><i class="fas fa-lock"></i></span>
                    <input type="password" name="password" class="form-control" required placeholder="Enter password">
                </div>
            </div>
            <button type="submit" class="btn btn-temple w-100 py-2">
                <i class="fas fa-sign-in-alt"></i> Login
            </button>
        </form>
    </div>
</div>
{% endblock %}
"""

DASHBOARD_TEMPLATE = """
{% extends "main" %}
{% block content %}
<!-- News Ticker -->
<div class="news-ticker-container">
    <div class="news-ticker">
        {% for msg in ticker_messages %}
        <span>🎂 {{ msg }}</span>
        {% endfor %}
        {% if not ticker_messages %}
        <span>🕉️ Welcome to Temple Management System 🙏</span>
        {% endif %}
    </div>
</div>

<!-- Period Selector -->
<div class="text-center mb-4">
    <button class="period-btn {% if period == 'daily' %}active{% endif %}" onclick="location.href='?period=daily'">Daily</button>
    <button class="period-btn {% if period == 'weekly' %}active{% endif %}" onclick="location.href='?period=weekly'">Weekly</button>
    <button class="period-btn {% if period == 'monthly' %}active{% endif %}" onclick="location.href='?period=monthly'">Monthly</button>
    <button class="period-btn {% if period == 'yearly' %}active{% endif %}" onclick="location.href='?period=yearly'">Yearly</button>
</div>

<!-- Stats Cards -->
<div class="row mb-4">
    <div class="col-md-3 mb-3">
        <div class="stat-card income">
            <i class="fas fa-arrow-up stat-icon"></i>
            <h6>{{ period|title }} Income</h6>
            <h3>₹{{ '{:,.2f}'.format(total_income) }}</h3>
        </div>
    </div>
    <div class="col-md-3 mb-3">
        <div class="stat-card expense">
            <i class="fas fa-arrow-down stat-icon"></i>
            <h6>{{ period|title }} Expenses</h6>
            <h3>₹{{ '{:,.2f}'.format(total_expenses) }}</h3>
        </div>
    </div>
    <div class="col-md-3 mb-3">
        <div class="stat-card devotees">
            <i class="fas fa-users stat-icon"></i>
            <h6>Total Devotees</h6>
            <h3>{{ total_devotees }}</h3>
        </div>
    </div>
    <div class="col-md-3 mb-3">
        <div class="stat-card bills">
            <i class="fas fa-file-invoice stat-icon"></i>
            <h6>{{ period|title }} Bills</h6>
            <h3>{{ total_bills }}</h3>
        </div>
    </div>
</div>

<div class="row">
    <!-- Daily Pooja -->
    <div class="col-md-6 mb-4">
        <div class="content-card">
            <h5><i class="fas fa-om"></i> Today's Pooja Schedule</h5>
            {% for pooja in daily_poojas %}
            <div class="pooja-card">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <strong>{{ pooja.pooja_name }}</strong>
                        <br><small class="text-muted">{{ pooja.description or '' }}</small>
                    </div>
                    <span class="pooja-time">{{ pooja.pooja_time or 'TBD' }}</span>
                </div>
            </div>
            {% endfor %}
            {% if not daily_poojas %}
            <p class="text-muted text-center py-3">No pooja scheduled today</p>
            {% endif %}
        </div>
    </div>

    <!-- Today's Birthdays -->
    <div class="col-md-6 mb-4">
        <div class="content-card">
            <h5><i class="fas fa-birthday-cake"></i> Today's Birthdays</h5>
            {% for d in birthdays %}
            <div class="d-flex align-items-center p-2 mb-2" style="background: #FFF8DC; border-radius: 8px;">
                <div style="width: 40px; height: 40px; background: #DC143C; color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 12px;">
                    🎂
                </div>
                <div>
                    <strong>{{ d.name }}</strong>
                    <br><small class="text-muted">{{ d.mobile_no or '' }}</small>
                </div>
            </div>
            {% endfor %}
            {% if not birthdays %}
            <p class="text-muted text-center py-3">No birthdays today</p>
            {% endif %}
        </div>
    </div>
</div>

<!-- Recent Bills -->
<div class="content-card">
    <h5><i class="fas fa-file-invoice"></i> Recent Bills</h5>
    <div class="table-responsive">
        <table class="table table-hover">
            <thead>
                <tr>
                    <th>Bill No</th>
                    <th>Date</th>
                    <th>Name</th>
                    <th>Pooja</th>
                    <th>Amount</th>
                </tr>
            </thead>
            <tbody>
                {% for bill in recent_bills %}
                <tr>
                    <td>{{ bill.bill_number }}</td>
                    <td>{{ bill.bill_date.strftime('%d/%m/%Y') }}</td>
                    <td>{{ bill.devotee.name if bill.devotee else bill.guest_name }}</td>
                    <td>{{ bill.pooja_type.name if bill.pooja_type else '-' }}</td>
                    <td><strong>₹{{ '{:,.2f}'.format(bill.amount) }}</strong></td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
"""

DEVOTEES_TEMPLATE = """
{% extends "main" %}
{% block content %}
<div class="content-card">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h5 class="mb-0"><i class="fas fa-users"></i> Enrolled Devotees</h5>
        <a href="{{ url_for('add_devotee') }}" class="btn btn-temple">
            <i class="fas fa-plus"></i> Add New Devotee
        </a>
    </div>

    <!-- Search -->
    <div class="row mb-3">
        <div class="col-md-4">
            <input type="text" id="searchInput" class="form-control" placeholder="Search by name, mobile, address..."
                   onkeyup="filterTable()">
        </div>
    </div>

    <div class="table-responsive">
        <table class="table table-hover" id="devoteesTable">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Photo</th>
                    <th>Name</th>
                    <th>Mobile</th>
                    <th>WhatsApp</th>
                    <th>Natchathiram</th>
                    <th>Family Members</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for d in devotees %}
                <tr>
                    <td>{{ d.id }}</td>
                    <td>
                        {% if d.photo_filename %}
                        <img src="{{ url_for('uploaded_file', folder='devotees', filename=d.photo_filename) }}"
                             class="photo-preview" style="width:40px;height:40px;">
                        {% else %}
                        <div style="width:40px;height:40px;background:#8B0000;color:#FFD700;border-radius:50%;
                                    display:flex;align-items:center;justify-content:center;font-weight:bold;">
                            {{ d.name[0] }}
                        </div>
                        {% endif %}
                    </td>
                    <td><strong>{{ d.name }}</strong></td>
                    <td>{{ d.mobile_no or '-' }}</td>
                    <td>{{ d.whatsapp_no or '-' }}</td>
                    <td>{{ d.natchathiram or '-' }}</td>
                    <td><span class="badge-temple">{{ d.family_members.count() }} members</span></td>
                    <td>
                        <a href="{{ url_for('view_devotee', id=d.id) }}" class="btn btn-sm btn-info text-white"
                           title="View"><i class="fas fa-eye"></i></a>
                        <a href="{{ url_for('edit_devotee', id=d.id) }}" class="btn btn-sm btn-warning"
                           title="Edit"><i class="fas fa-edit"></i></a>
                        <form method="POST" action="{{ url_for('delete_devotee', id=d.id) }}"
                              style="display:inline" onsubmit="return confirm('Delete this devotee and all family members?')">
                            <button class="btn btn-sm btn-danger" title="Delete"><i class="fas fa-trash"></i></button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
{% block extra_js %}
<script>
function filterTable() {
    var input = document.getElementById("searchInput").value.toLowerCase();
    var rows = document.querySelectorAll("#devoteesTable tbody tr");
    rows.forEach(function(row) {
        var text = row.textContent.toLowerCase();
        row.style.display = text.includes(input) ? "" : "none";
    });
}
</script>
{% endblock %}
"""

ADD_DEVOTEE_TEMPLATE = """
{% extends "main" %}
{% block content %}
<div class="content-card">
    <h5><i class="fas fa-user-plus"></i> {{ 'Edit' if devotee else 'Add New' }} Devotee (Family Head)</h5>
    <form method="POST" enctype="multipart/form-data" id="devoteeForm">
        <div class="row">
            <div class="col-md-8">
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Name *</label>
                        <input type="text" name="name" class="form-control" required
                               value="{{ devotee.name if devotee else '' }}">
                    </div>
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Date of Birth</label>
                        <input type="date" name="dob" class="form-control"
                               value="{{ devotee.dob.strftime('%Y-%m-%d') if devotee and devotee.dob else '' }}">
                    </div>
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Relation Type</label>
                        <select name="relation_type" class="form-select">
                            <option value="">-- Select --</option>
                            {% for r in relation_types %}
                            <option value="{{ r }}" {{ 'selected' if devotee and devotee.relation_type == r else '' }}>{{ r }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Mobile No</label>
                        <input type="text" name="mobile_no" class="form-control"
                               value="{{ devotee.mobile_no if devotee else '' }}">
                    </div>
                    <div class="col-md-6 mb-3">
                        <label class="form-label">WhatsApp No</label>
                        <input type="text" name="whatsapp_no" class="form-control"
                               value="{{ devotee.whatsapp_no if devotee else '' }}">
                    </div>
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Wedding Day</label>
                        <input type="date" name="wedding_day" class="form-control"
                               value="{{ devotee.wedding_day.strftime('%Y-%m-%d') if devotee and devotee.wedding_day else '' }}">
                    </div>
                    <div class="col-md-6 mb-3">
                        <label class="form-label">Natchathiram</label>
                        <select name="natchathiram" class="form-select">
                            <option value="">-- Select --</option>
                            {% for n in natchathiram_list %}
                            <option value="{{ n }}" {{ 'selected' if devotee and devotee.natchathiram == n else '' }}>{{ n }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="col-md-12 mb-3">
                        <label class="form-label">Address</label>
                        <textarea name="address" class="form-control" rows="2">{{ devotee.address if devotee else '' }}</textarea>
                    </div>
                </div>
            </div>
            <div class="col-md-4 text-center">
                <label class="form-label">Photo</label>
                <div class="mb-2">
                    {% if devotee and devotee.photo_filename %}
                    <img src="{{ url_for('uploaded_file', folder='devotees', filename=devotee.photo_filename) }}"
                         class="photo-preview" id="photoPreview" style="width:150px;height:150px;">
                    {% else %}
                    <div id="photoPreview" style="width:150px;height:150px;background:#f0f0f0;border-radius:50%;
                         display:flex;align-items:center;justify-content:center;margin:auto;border:3px dashed #ccc;">
                        <i class="fas fa-camera fa-2x text-muted"></i>
                    </div>
                    {% endif %}
                </div>
                <input type="file" name="photo" class="form-control" accept="image/*"
                       onchange="previewPhoto(this)">
            </div>
        </div>

        <!-- Yearly Pooja Section -->
        <div class="mt-4">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h6 style="color: #8B0000; font-weight: 700;"><i class="fas fa-om"></i> Yearly Pooja</h6>
                <button type="button" class="btn btn-sm btn-gold" onclick="addYearlyPooja()">
                    <i class="fas fa-plus"></i> Add Pooja
                </button>
            </div>
            <div id="yearlyPoojaContainer">
                {% if devotee %}
                {% for yp in devotee.yearly_poojas.all() %}
                <div class="yearly-pooja-entry" id="yp_{{ loop.index0 }}">
                    <input type="hidden" name="yp_id[]" value="{{ yp.id }}">
                    <div class="row">
                        <div class="col-md-4 mb-2">
                            <select name="yp_pooja_type[]" class="form-select form-select-sm">
                                <option value="">-- Select Pooja --</option>
                                {% for pt in pooja_types %}
                                <option value="{{ pt.id }}" {{ 'selected' if yp.pooja_type_id == pt.id else '' }}>{{ pt.name }}</option>
                                {% endfor %}
                            </select>
                        </div>
                        <div class="col-md-3 mb-2">
                            <input type="text" name="yp_pooja_name[]" class="form-control form-control-sm"
                                   placeholder="Custom name" value="{{ yp.pooja_name or '' }}">
                        </div>
                        <div class="col-md-3 mb-2">
                            <input type="date" name="yp_pooja_date[]" class="form-control form-control-sm"
                                   value="{{ yp.pooja_date.strftime('%Y-%m-%d') if yp.pooja_date else '' }}">
                        </div>
                        <div class="col-md-2 mb-2">
                            <button type="button" class="btn btn-sm btn-danger" onclick="this.closest('.yearly-pooja-entry').remove()">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                    </div>
                    <input type="text" name="yp_notes[]" class="form-control form-control-sm" placeholder="Notes"
                           value="{{ yp.notes or '' }}">
                </div>
                {% endfor %}
                {% endif %}
            </div>
        </div>

        <!-- Family Members Section -->
        <div class="mt-4">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h6 style="color: #8B0000; font-weight: 700;"><i class="fas fa-users"></i> Family Members</h6>
                <button type="button" class="btn btn-sm btn-gold" onclick="addFamilyMember()">
                    <i class="fas fa-plus"></i> Add Member
                </button>
            </div>
            <div id="familyMembersContainer">
                {% if devotee %}
                {% for fm in devotee.family_members.all() %}
                <div class="family-member-card" id="fm_{{ loop.index0 }}">
                    <input type="hidden" name="fm_id[]" value="{{ fm.id }}">
                    <button type="button" class="btn btn-sm btn-danger position-absolute" style="top:5px;right:5px;"
                            onclick="this.closest('.family-member-card').remove()">
                        <i class="fas fa-times"></i>
                    </button>
                    <div class="row">
                        <div class="col-md-3 mb-2">
                            <label class="form-label">Name *</label>
                            <input type="text" name="fm_name[]" class="form-control form-control-sm" required
                                   value="{{ fm.name }}">
                        </div>
                        <div class="col-md-2 mb-2">
                            <label class="form-label">DOB</label>
                            <input type="date" name="fm_dob[]" class="form-control form-control-sm"
                                   value="{{ fm.dob.strftime('%Y-%m-%d') if fm.dob else '' }}">
                        </div>
                        <div class="col-md-2 mb-2">
                            <label class="form-label">Relation</label>
                            <select name="fm_relation[]" class="form-select form-select-sm">
                                <option value="">--</option>
                                {% for r in relation_types %}
                                <option value="{{ r }}" {{ 'selected' if fm.relation_type == r else '' }}>{{ r }}</option>
                                {% endfor %}
                            </select>
                        </div>
                        <div class="col-md-2 mb-2">
                            <label class="form-label">Wedding Day</label>
                            <input type="date" name="fm_wedding[]" class="form-control form-control-sm"
                                   value="{{ fm.wedding_day.strftime('%Y-%m-%d') if fm.wedding_day else '' }}">
                        </div>
                        <div class="col-md-3 mb-2">
                            <label class="form-label">Natchathiram</label>
                            <select name="fm_natchathiram[]" class="form-select form-select-sm">
                                <option value="">--</option>
                                {% for n in natchathiram_list %}
                                <option value="{{ n }}" {{ 'selected' if fm.natchathiram == n else '' }}>{{ n }}</option>
                                {% endfor %}
                            </select>
                        </div>
                    </div>
                </div>
                {% endfor %}
                {% endif %}
            </div>
        </div>

        <div class="mt-4 text-center">
            <a href="{{ url_for('devotees') }}" class="btn btn-secondary me-2">Cancel</a>
            <button type="submit" class="btn btn-temple">
                <i class="fas fa-save"></i> {{ 'Update' if devotee else 'Save' }} Devotee
            </button>
        </div>
    </form>
</div>
{% endblock %}
{% block extra_js %}
<script>
var fmIndex = {{ devotee.family_members.count() if devotee else 0 }};
var ypIndex = {{ devotee.yearly_poojas.count() if devotee else 0 }};

function addFamilyMember() {
    var html = `
    <div class="family-member-card" id="fm_${fmIndex}">
        <input type="hidden" name="fm_id[]" value="0">
        <button type="button" class="btn btn-sm btn-danger position-absolute" style="top:5px;right:5px;"
                onclick="this.closest('.family-member-card').remove()">
            <i class="fas fa-times"></i>
        </button>
        <div class="row">
            <div class="col-md-3 mb-2">
                <label class="form-label">Name *</label>
                <input type="text" name="fm_name[]" class="form-control form-control-sm" required>
            </div>
            <div class="col-md-2 mb-2">
                <label class="form-label">DOB</label>
                <input type="date" name="fm_dob[]" class="form-control form-control-sm">
            </div>
            <div class="col-md-2 mb-2">
                <label class="form-label">Relation</label>
                <select name="fm_relation[]" class="form-select form-select-sm">
                    <option value="">--</option>
                    {% for r in relation_types %}
                    <option value="{{ r }}">{{ r }}</option>
                    {% endfor %}
                </select>
            </div>
            <div class="col-md-2 mb-2">
                <label class="form-label">Wedding Day</label>
                <input type="date" name="fm_wedding[]" class="form-control form-control-sm">
            </div>
            <div class="col-md-3 mb-2">
                <label class="form-label">Natchathiram</label>
                <select name="fm_natchathiram[]" class="form-select form-select-sm">
                    <option value="">--</option>
                    {% for n in natchathiram_list %}
                    <option value="{{ n }}">{{ n }}</option>
                    {% endfor %}
                </select>
            </div>
        </div>
    </div>`;
    document.getElementById('familyMembersContainer').insertAdjacentHTML('beforeend', html);
    fmIndex++;
}

function addYearlyPooja() {
    var html = `
    <div class="yearly-pooja-entry" id="yp_${ypIndex}">
        <input type="hidden" name="yp_id[]" value="0">
        <div class="row">
            <div class="col-md-4 mb-2">
                <select name="yp_pooja_type[]" class="form-select form-select-sm">
                    <option value="">-- Select Pooja --</option>
                    {% for pt in pooja_types %}
                    <option value="{{ pt.id }}">{{ pt.name }}</option>
                    {% endfor %}
                </select>
            </div>
            <div class="col-md-3 mb-2">
                <input type="text" name="yp_pooja_name[]" class="form-control form-control-sm" placeholder="Custom name">
            </div>
            <div class="col-md-3 mb-2">
                <input type="date" name="yp_pooja_date[]" class="form-control form-control-sm">
            </div>
            <div class="col-md-2 mb-2">
                <button type="button" class="btn btn-sm btn-danger" onclick="this.closest('.yearly-pooja-entry').remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        </div>
        <input type="text" name="yp_notes[]" class="form-control form-control-sm" placeholder="Notes">
    </div>`;
    document.getElementById('yearlyPoojaContainer').insertAdjacentHTML('beforeend', html);
    ypIndex++;
}

function previewPhoto(input) {
    if (input.files && input.files[0]) {
        var reader = new FileReader();
        reader.onload = function(e) {
            var preview = document.getElementById('photoPreview');
            if (preview.tagName === 'IMG') {
                preview.src = e.target.result;
            } else {
                preview.outerHTML = '<img src="' + e.target.result + '" class="photo-preview" id="photoPreview" style="width:150px;height:150px;">';
            }
        }
        reader.readAsDataURL(input.files[0]);
    }
}
</script>
{% endblock %}
"""

VIEW_DEVOTEE_TEMPLATE = """
{% extends "main" %}
{% block content %}
<div class="content-card">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h5 class="mb-0"><i class="fas fa-user"></i> Devotee Details</h5>
        <div>
            <a href="{{ url_for('edit_devotee', id=devotee.id) }}" class="btn btn-warning btn-sm">
                <i class="fas fa-edit"></i> Edit
            </a>
            <a href="{{ url_for('devotees') }}" class="btn btn-secondary btn-sm">
                <i class="fas fa-arrow-left"></i> Back
            </a>
        </div>
    </div>

    <div class="row">
        <div class="col-md-3 text-center">
            {% if devotee.photo_filename %}
            <img src="{{ url_for('uploaded_file', folder='devotees', filename=devotee.photo_filename) }}"
                 class="photo-preview" style="width:150px;height:150px;">
            {% else %}
            <div style="width:150px;height:150px;background:#8B0000;color:#FFD700;border-radius:50%;
                 display:flex;align-items:center;justify-content:center;margin:auto;font-size:3em;font-weight:bold;">
                {{ devotee.name[0] }}
            </div>
            {% endif %}
            <h5 class="mt-2" style="color: #8B0000;">{{ devotee.name }}</h5>
            <span class="badge-temple">Family Head</span>
        </div>
        <div class="col-md-9">
            <div class="row">
                <div class="col-md-4 mb-2"><strong>DOB:</strong> {{ devotee.dob.strftime('%d/%m/%Y') if devotee.dob else '-' }}</div>
                <div class="col-md-4 mb-2"><strong>Mobile:</strong> {{ devotee.mobile_no or '-' }}</div>
                <div class="col-md-4 mb-2"><strong>WhatsApp:</strong> {{ devotee.whatsapp_no or '-' }}</div>
                <div class="col-md-4 mb-2"><strong>Relation:</strong> {{ devotee.relation_type or '-' }}</div>
                <div class="col-md-4 mb-2"><strong>Wedding Day:</strong> {{ devotee.wedding_day.strftime('%d/%m/%Y') if devotee.wedding_day else '-' }}</div>
                <div class="col-md-4 mb-2"><strong>Natchathiram:</strong> {{ devotee.natchathiram or '-' }}</div>
                <div class="col-md-12 mb-2"><strong>Address:</strong> {{ devotee.address or '-' }}</div>
            </div>
        </div>
    </div>

    <!-- Yearly Pooja -->
    {% if devotee.yearly_poojas.count() > 0 %}
    <hr>
    <h6 style="color: #8B0000;"><i class="fas fa-om"></i> Yearly Pooja</h6>
    <div class="table-responsive">
        <table class="table table-sm">
            <thead><tr><th>Pooja</th><th>Custom Name</th><th>Date</th><th>Notes</th></tr></thead>
            <tbody>
            {% for yp in devotee.yearly_poojas.all() %}
            <tr>
                <td>{{ yp.pooja_type.name if yp.pooja_type_id else '-' }}</td>
                <td>{{ yp.pooja_name or '-' }}</td>
                <td>{{ yp.pooja_date.strftime('%d/%m/%Y') if yp.pooja_date else '-' }}</td>
                <td>{{ yp.notes or '-' }}</td>
            </tr>
            {% endfor %}
            </tbody>
        </table>
    </div>
    {% endif %}

    <!-- Family Members -->
    {% set members = devotee.family_members.all() %}
    {% if members %}
    <hr>
    <h6 style="color: #8B0000;"><i class="fas fa-users"></i> Family Members ({{ members|length }})</h6>
    <div class="table-responsive">
        <table class="table table-sm table-hover">
            <thead><tr><th>Name</th><th>DOB</th><th>Relation</th><th>Wedding Day</th><th>Natchathiram</th></tr></thead>
            <tbody>
            {% for fm in members %}
            <tr>
                <td>{{ fm.name }}</td>
                <td>{{ fm.dob.strftime('%d/%m/%Y') if fm.dob else '-' }}</td>
                <td>{{ fm.relation_type or '-' }}</td>
                <td>{{ fm.wedding_day.strftime('%d/%m/%Y') if fm.wedding_day else '-' }}</td>
                <td>{{ fm.natchathiram or '-' }}</td>
            </tr>
            {% endfor %}
            </tbody>
        </table>
    </div>
    {% endif %}
</div>
{% endblock %}
"""

BILLING_TEMPLATE = """
{% extends "main" %}
{% block content %}
<div class="content-card">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h5 class="mb-0"><i class="fas fa-file-invoice"></i> Bills</h5>
        <a href="{{ url_for('new_bill') }}" class="btn btn-temple">
            <i class="fas fa-plus"></i> New Bill
        </a>
    </div>
    <div class="table-responsive">
        <table class="table table-hover data-table">
            <thead>
                <tr>
                    <th>Bill No</th>
                    <th>Manual No</th>
                    <th>Book No</th>
                    <th>Date</th>
                    <th>Type</th>
                    <th>Name</th>
                    <th>Pooja</th>
                    <th>Amount</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for bill in bills %}
                <tr class="{{ 'table-danger' if bill.is_deleted else '' }}">
                    <td>{{ bill.bill_number }}</td>
                    <td>{{ bill.manual_bill_no or '-' }}</td>
                    <td>{{ bill.bill_book_no or '-' }}</td>
                    <td>{{ bill.bill_date.strftime('%d/%m/%Y') }}</td>
                    <td><span class="badge {{ 'bg-success' if bill.devotee_type == 'enrolled' else 'bg-warning' }}">
                        {{ bill.devotee_type }}</span></td>
                    <td>{{ bill.devotee.name if bill.devotee else bill.guest_name }}</td>
                    <td>{{ bill.pooja_type.name if bill.pooja_type else '-' }}</td>
                    <td><strong>₹{{ '{:,.2f}'.format(bill.amount) }}</strong></td>
                    <td>
                        <a href="{{ url_for('view_bill', id=bill.id) }}" class="btn btn-sm btn-info text-white">
                            <i class="fas fa-eye"></i>
                        </a>
                        {% if current_user.role == 'admin' and not bill.is_deleted %}
                        <form method="POST" action="{{ url_for('delete_bill', id=bill.id) }}"
                              style="display:inline" onsubmit="return confirm('Delete this bill?')">
                            <button class="btn btn-sm btn-danger"><i class="fas fa-trash"></i></button>
                        </form>
                        {% endif %}
                        {% if bill.is_deleted %}
                        <span class="badge bg-danger">Deleted</span>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
"""

NEW_BILL_TEMPLATE = """
{% extends "main" %}
{% block content %}
<div class="content-card">
    <h5><i class="fas fa-file-invoice"></i> New Bill</h5>
    <form method="POST" id="billForm">
        <div class="row">
            <div class="col-md-3 mb-3">
                <label class="form-label">Pooja Type *</label>
                <select name="pooja_type_id" class="form-select" required onchange="updateAmount(this)">
                    <option value="">-- Select Pooja --</option>
                    {% for pt in pooja_types %}
                    <option value="{{ pt.id }}" data-amount="{{ pt.amount }}">{{ pt.name }} (₹{{ pt.amount }})</option>
                    {% endfor %}
                </select>
            </div>
            <div class="col-md-3 mb-3">
                <label class="form-label">Manual Bill No</label>
                <input type="text" name="manual_bill_no" class="form-control">
            </div>
            <div class="col-md-3 mb-3">
                <label class="form-label">Bill Book No</label>
                <input type="text" name="bill_book_no" class="form-control">
            </div>
            <div class="col-md-3 mb-3">
                <label class="form-label">Amount *</label>
                <input type="number" name="amount" id="amountField" class="form-control" step="0.01" required>
            </div>
        </div>

        <!-- Devotee Type Selection -->
        <div class="row mb-3">
            <div class="col-md-12">
                <div class="btn-group" role="group">
                    <input type="radio" class="btn-check" name="devotee_type" id="enrolledBtn"
                           value="enrolled" checked onchange="toggleDevoteeType('enrolled')">
                    <label class="btn btn-outline-success" for="enrolledBtn">
                        <i class="fas fa-user-check"></i> Enrolled Devotee
                    </label>
                    <input type="radio" class="btn-check" name="devotee_type" id="guestBtn"
                           value="guest" onchange="toggleDevoteeType('guest')">
                    <label class="btn btn-outline-warning" for="guestBtn">
                        <i class="fas fa-user-plus"></i> Guest Devotee
                    </label>
                </div>
            </div>
        </div>

        <!-- Enrolled Devotee Section -->
        <div id="enrolledSection">
            <div class="row mb-3">
                <div class="col-md-8">
                    <label class="form-label">Search Devotee (Name / Mobile / WhatsApp / Address)</label>
                    <input type="text" id="devoteeSearch" class="form-control"
                           placeholder="Type to search..." onkeyup="searchDevotee(this.value)">
                    <input type="hidden" name="devotee_id" id="devoteeId">
                    <div id="searchResults" class="list-group mt-1" style="max-height:200px;overflow-y:auto;display:none;"></div>
                </div>
            </div>
            <div id="selectedDevotee" style="display:none;" class="alert alert-success">
                <strong id="selDevName"></strong><br>
                <span id="selDevAddress"></span><br>
                <small id="selDevMobile"></small>
            </div>
        </div>

        <!-- Guest Devotee Section -->
        <div id="guestSection" style="display:none;">
            <div class="row">
                <div class="col-md-4 mb-3">
                    <label class="form-label">Guest Name *</label>
                    <input type="text" name="guest_name" class="form-control">
                </div>
                <div class="col-md-4 mb-3">
                    <label class="form-label">Mobile No</label>
                    <input type="text" name="guest_mobile" class="form-control">
                </div>
                <div class="col-md-4 mb-3">
                    <label class="form-label">WhatsApp No</label>
                    <input type="text" name="guest_whatsapp" class="form-control">
                </div>
                <div class="col-md-12 mb-3">
                    <label class="form-label">Address</label>
                    <textarea name="guest_address" class="form-control" rows="2"></textarea>
                </div>
            </div>
        </div>

        <div class="mb-3">
            <label class="form-label">Notes</label>
            <textarea name="notes" class="form-control" rows="2"></textarea>
        </div>

        <div class="text-center">
            <a href="{{ url_for('billing') }}" class="btn btn-secondary me-2">Cancel</a>
            <button type="submit" class="btn btn-temple">
                <i class="fas fa-save"></i> Generate Bill
            </button>
        </div>
    </form>
</div>
{% endblock %}
{% block extra_js %}
<script>
function toggleDevoteeType(type) {
    document.getElementById('enrolledSection').style.display = type === 'enrolled' ? '' : 'none';
    document.getElementById('guestSection').style.display = type === 'guest' ? '' : 'none';
}

function updateAmount(sel) {
    var opt = sel.options[sel.selectedIndex];
    if (opt.dataset.amount) {
        document.getElementById('amountField').value = opt.dataset.amount;
    }
}

function searchDevotee(query) {
    if (query.length < 2) {
        document.getElementById('searchResults').style.display = 'none';
        return;
    }
    fetch('/api/search_devotees?q=' + encodeURIComponent(query))
        .then(r => r.json())
        .then(data => {
            var html = '';
            data.forEach(function(d) {
                html += '<a href="#" class="list-group-item list-group-item-action" ' +
                    'onclick="selectDevotee(' + d.id + ',\\'' + d.name.replace("'","\\'") + '\\',\\'' +
                    (d.address||'').replace("'","\\'") + '\\',\\'' + (d.mobile||'') + '\\');return false;">' +
                    '<strong>' + d.name + '</strong> - ' + (d.mobile||'') + '<br><small>' + (d.address||'') + '</small></a>';
            });
            document.getElementById('searchResults').innerHTML = html;
            document.getElementById('searchResults').style.display = html ? '' : 'none';
        });
}

function selectDevotee(id, name, address, mobile) {
    document.getElementById('devoteeId').value = id;
    document.getElementById('selDevName').textContent = name;
    document.getElementById('selDevAddress').textContent = address;
    document.getElementById('selDevMobile').textContent = 'Mobile: ' + mobile;
    document.getElementById('selectedDevotee').style.display = '';
    document.getElementById('searchResults').style.display = 'none';
    document.getElementById('devoteeSearch').value = name;
}
</script>
{% endblock %}
"""

VIEW_BILL_TEMPLATE = """
{% extends "main" %}
{% block content %}
<div class="content-card" id="billPrint">
    <div class="text-center mb-4">
        <h4 style="color: #8B0000;">🕉️ Temple Management</h4>
        <h5>Bill / Receipt</h5>
        <hr style="border-color: #FFD700;">
    </div>
    <div class="row mb-3">
        <div class="col-md-6">
            <strong>Bill No:</strong> {{ bill.bill_number }}<br>
            <strong>Manual Bill No:</strong> {{ bill.manual_bill_no or '-' }}<br>
            <strong>Bill Book No:</strong> {{ bill.bill_book_no or '-' }}
        </div>
        <div class="col-md-6 text-end">
            <strong>Date:</strong> {{ bill.bill_date.strftime('%d/%m/%Y %I:%M %p') }}
        </div>
    </div>
    <hr>
    <div class="row mb-3">
        <div class="col-md-6">
            <strong>Devotee Type:</strong>
            <span class="badge {{ 'bg-success' if bill.devotee_type == 'enrolled' else 'bg-warning' }}">
                {{ bill.devotee_type|title }}</span><br>
            <strong>Name:</strong> {{ bill.devotee.name if bill.devotee else bill.guest_name }}<br>
            <strong>Address:</strong> {{ bill.devotee.address if bill.devotee else bill.guest_address }}<br>
            {% if bill.devotee_type == 'guest' %}
            <strong>Mobile:</strong> {{ bill.guest_mobile or '-' }}<br>
            <strong>WhatsApp:</strong> {{ bill.guest_whatsapp or '-' }}
            {% else %}
            <strong>Mobile:</strong> {{ bill.devotee.mobile_no if bill.devotee else '-' }}
            {% endif %}
        </div>
        <div class="col-md-6">
            <strong>Pooja Type:</strong> {{ bill.pooja_type.name if bill.pooja_type else '-' }}<br>
            <strong>Notes:</strong> {{ bill.notes or '-' }}
        </div>
    </div>
    <hr>
    <div class="text-center">
        <h3 style="color: #228B22;">Amount: ₹{{ '{:,.2f}'.format(bill.amount) }}</h3>
    </div>
    <hr>
    {% if bill.is_deleted %}
    <div class="alert alert-danger text-center"><strong>This bill has been DELETED</strong></div>
    {% endif %}
</div>
<div class="text-center mt-3 no-print">
    <a href="{{ url_for('billing') }}" class="btn btn-secondary me-2">
        <i class="fas fa-arrow-left"></i> Back
    </a>
    <button onclick="window.print()" class="btn btn-temple">
        <i class="fas fa-print"></i> Print Bill
    </button>
</div>
{% endblock %}
"""

EXPENSES_TEMPLATE = """
{% extends "main" %}
{% block content %}
<div class="row">
    <div class="col-md-4">
        <div class="content-card">
            <h5><i class="fas fa-plus"></i> Add Expense</h5>
            <form method="POST">
                <div class="mb-3">
                    <label class="form-label">Expense Type *</label>
                    <select name="expense_type_id" class="form-select" required>
                        <option value="">-- Select --</option>
                        {% for et in expense_types %}
                        <option value="{{ et.id }}">{{ et.name }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="mb-3">
                    <label class="form-label">Amount *</label>
                    <input type="number" name="amount" class="form-control" step="0.01" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Date</label>
                    <input type="date" name="expense_date" class="form-control" value="{{ today }}">
                </div>
                <div class="mb-3">
                    <label class="form-label">Description</label>
                    <textarea name="description" class="form-control" rows="2"></textarea>
                </div>
                <button type="submit" class="btn btn-temple w-100">
                    <i class="fas fa-save"></i> Save Expense
                </button>
            </form>
        </div>
    </div>
    <div class="col-md-8">
        <div class="content-card">
            <h5><i class="fas fa-list"></i> Recent Expenses</h5>
            <div class="table-responsive">
                <table class="table table-hover data-table">
                    <thead>
                        <tr><th>Date</th><th>Type</th><th>Amount</th><th>Description</th><th>Action</th></tr>
                    </thead>
                    <tbody>
                        {% for exp in expenses %}
                        <tr>
                            <td>{{ exp.expense_date.strftime('%d/%m/%Y') if exp.expense_date else '-' }}</td>
                            <td>{{ exp.expense_type.name if exp.expense_type else '-' }}</td>
                            <td><strong>₹{{ '{:,.2f}'.format(exp.amount) }}</strong></td>
                            <td>{{ exp.description or '-' }}</td>
                            <td>
                                <form method="POST" action="{{ url_for('delete_expense', id=exp.id) }}"
                                      style="display:inline" onsubmit="return confirm('Delete?')">
                                    <button class="btn btn-sm btn-danger"><i class="fas fa-trash"></i></button>
                                </form>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>
{% endblock %}
"""

REPORTS_TEMPLATE = """
{% extends "main" %}
{% block content %}
<div class="content-card">
    <h5><i class="fas fa-chart-bar"></i> Reports</h5>
    <form method="GET" class="row mb-4">
        <div class="col-md-2 mb-2">
            <label class="form-label">Period</label>
            <select name="period" class="form-select" onchange="toggleCustom(this)">
                <option value="daily" {{ 'selected' if period == 'daily' else '' }}>Daily</option>
                <option value="weekly" {{ 'selected' if period == 'weekly' else '' }}>Weekly</option>
                <option value="monthly" {{ 'selected' if period == 'monthly' else '' }}>Monthly</option>
                <option value="yearly" {{ 'selected' if period == 'yearly' else '' }}>Yearly</option>
                <option value="custom" {{ 'selected' if period == 'custom' else '' }}>Custom Date</option>
            </select>
        </div>
        <div class="col-md-2 mb-2" id="dateFrom" style="{{ '' if period == 'custom' else 'display:none' }}">
            <label class="form-label">From</label>
            <input type="date" name="date_from" class="form-control" value="{{ date_from }}">
        </div>
        <div class="col-md-2 mb-2" id="dateTo" style="{{ '' if period == 'custom' else 'display:none' }}">
            <label class="form-label">To</label>
            <input type="date" name="date_to" class="form-control" value="{{ date_to }}">
        </div>
        <div class="col-md-3 mb-2">
            <label class="form-label">Pooja Type</label>
            <select name="pooja_type_id" class="form-select">
                <option value="">All</option>
                {% for pt in pooja_types %}
                <option value="{{ pt.id }}" {{ 'selected' if pooja_type_filter == pt.id|string else '' }}>{{ pt.name }}</option>
                {% endfor %}
            </select>
        </div>
        <div class="col-md-2 mb-2 d-flex align-items-end">
            <button type="submit" class="btn btn-temple w-100">
                <i class="fas fa-filter"></i> Filter
            </button>
        </div>
        <div class="col-md-1 mb-2 d-flex align-items-end">
            <button type="button" onclick="window.print()" class="btn btn-gold w-100">
                <i class="fas fa-print"></i>
            </button>
        </div>
    </form>

    <!-- Summary -->
    <div class="row mb-4">
        <div class="col-md-4">
            <div class="stat-card income py-3">
                <h6>Total Income</h6>
                <h4>₹{{ '{:,.2f}'.format(total_income) }}</h4>
            </div>
        </div>
        <div class="col-md-4">
            <div class="stat-card expense py-3">
                <h6>Total Expenses</h6>
                <h4>₹{{ '{:,.2f}'.format(total_expenses) }}</h4>
            </div>
        </div>
        <div class="col-md-4">
            <div class="stat-card devotees py-3">
                <h6>Net Balance</h6>
                <h4>₹{{ '{:,.2f}'.format(total_income - total_expenses) }}</h4>
            </div>
        </div>
    </div>

    <!-- Income Details -->
    <h6 style="color:#228B22; font-weight:700;"><i class="fas fa-arrow-up"></i> Income (Bills)</h6>
    <div class="table-responsive mb-4">
        <table class="table table-sm table-hover">
            <thead><tr><th>Bill No</th><th>Date</th><th>Name</th><th>Pooja</th><th>Amount</th></tr></thead>
            <tbody>
                {% for bill in bills %}
                <tr>
                    <td>{{ bill.bill_number }}</td>
                    <td>{{ bill.bill_date.strftime('%d/%m/%Y') }}</td>
                    <td>{{ bill.devotee.name if bill.devotee else bill.guest_name }}</td>
                    <td>{{ bill.pooja_type.name if bill.pooja_type else '-' }}</td>
                    <td>₹{{ '{:,.2f}'.format(bill.amount) }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <!-- Expense Details -->
    <h6 style="color:#DC143C; font-weight:700;"><i class="fas fa-arrow-down"></i> Expenses</h6>
    <div class="table-responsive">
        <table class="table table-sm table-hover">
            <thead><tr><th>Date</th><th>Type</th><th>Description</th><th>Amount</th></tr></thead>
            <tbody>
                {% for exp in expenses %}
                <tr>
                    <td>{{ exp.expense_date.strftime('%d/%m/%Y') if exp.expense_date else '-' }}</td>
                    <td>{{ exp.expense_type.name if exp.expense_type else '-' }}</td>
                    <td>{{ exp.description or '-' }}</td>
                    <td>₹{{ '{:,.2f}'.format(exp.amount) }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
{% block extra_js %}
<script>
function toggleCustom(sel) {
    var show = sel.value === 'custom';
    document.getElementById('dateFrom').style.display = show ? '' : 'none';
    document.getElementById('dateTo').style.display = show ? '' : 'none';
}
</script>
{% endblock %}
"""

SETTINGS_TEMPLATE = """
{% extends "main" %}
{% block content %}
<div class="row">
    <!-- Pooja Types -->
    <div class="col-md-6 mb-4">
        <div class="content-card">
            <h5><i class="fas fa-om"></i> Pooja Types</h5>
            <form method="POST" action="{{ url_for('add_pooja_type') }}" class="row mb-3">
                <div class="col-5">
                    <input type="text" name="name" class="form-control form-control-sm" placeholder="Pooja Name" required>
                </div>
                <div class="col-4">
                    <input type="number" name="amount" class="form-control form-control-sm" placeholder="Amount" step="0.01">
                </div>
                <div class="col-3">
                    <button class="btn btn-temple btn-sm w-100">Add</button>
                </div>
            </form>
            <table class="table table-sm">
                <thead><tr><th>Name</th><th>Amount</th><th>Action</th></tr></thead>
                <tbody>
                {% for pt in pooja_types %}
                <tr>
                    <td>{{ pt.name }}</td>
                    <td>₹{{ pt.amount }}</td>
                    <td>
                        <form method="POST" action="{{ url_for('delete_pooja_type', id=pt.id) }}"
                              style="display:inline" onsubmit="return confirm('Delete?')">
                            <button class="btn btn-sm btn-danger"><i class="fas fa-trash"></i></button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

    <!-- Expense Types -->
    <div class="col-md-6 mb-4">
        <div class="content-card">
            <h5><i class="fas fa-tags"></i> Expense Types</h5>
            <form method="POST" action="{{ url_for('add_expense_type') }}" class="row mb-3">
                <div class="col-8">
                    <input type="text" name="name" class="form-control form-control-sm" placeholder="Expense Type Name" required>
                </div>
                <div class="col-4">
                    <button class="btn btn-temple btn-sm w-100">Add</button>
                </div>
            </form>
            <table class="table table-sm">
                <thead><tr><th>Name</th><th>Action</th></tr></thead>
                <tbody>
                {% for et in expense_types %}
                <tr>
                    <td>{{ et.name }}</td>
                    <td>
                        <form method="POST" action="{{ url_for('delete_expense_type', id=et.id) }}"
                              style="display:inline" onsubmit="return confirm('Delete?')">
                            <button class="btn btn-sm btn-danger"><i class="fas fa-trash"></i></button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>
{% endblock %}
"""

USER_MANAGEMENT_TEMPLATE = """
{% extends "main" %}
{% block content %}
<div class="content-card">
    <h5><i class="fas fa-user-shield"></i> User Management</h5>
    <form method="POST" class="row mb-4">
        <div class="col-md-3 mb-2">
            <input type="text" name="username" class="form-control" placeholder="Username" required>
        </div>
        <div class="col-md-3 mb-2">
            <input type="text" name="full_name" class="form-control" placeholder="Full Name">
        </div>
        <div class="col-md-2 mb-2">
            <input type="password" name="password" class="form-control" placeholder="Password" required>
        </div>
        <div class="col-md-2 mb-2">
            <select name="role" class="form-select">
                <option value="user">User</option>
                <option value="admin">Admin</option>
            </select>
        </div>
        <div class="col-md-2 mb-2">
            <button class="btn btn-temple w-100">Add User</button>
        </div>
    </form>
    <table class="table table-hover">
        <thead><tr><th>Username</th><th>Full Name</th><th>Role</th><th>Created</th><th>Action</th></tr></thead>
        <tbody>
        {% for user in users %}
        <tr>
            <td>{{ user.username }}</td>
            <td>{{ user.full_name or '-' }}</td>
            <td><span class="badge {{ 'bg-danger' if user.role == 'admin' else 'bg-primary' }}">{{ user.role }}</span></td>
            <td>{{ user.created_at.strftime('%d/%m/%Y') }}</td>
            <td>
                {% if user.username != 'admin' %}
                <form method="POST" action="{{ url_for('delete_user', id=user.id) }}"
                      style="display:inline" onsubmit="return confirm('Delete user?')">
                    <button class="btn btn-sm btn-danger"><i class="fas fa-trash"></i></button>
                </form>
                {% endif %}
            </td>
        </tr>
        {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}
"""

DAILY_POOJA_TEMPLATE = """
{% extends "main" %}
{% block content %}
<div class="row">
    <div class="col-md-5">
        <div class="content-card">
            <h5><i class="fas fa-plus"></i> Add Daily Pooja Schedule</h5>
            <form method="POST">
                <div class="mb-3">
                    <label class="form-label">Pooja Name *</label>
                    <input type="text" name="pooja_name" class="form-control" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Time</label>
                    <input type="text" name="pooja_time" class="form-control" placeholder="e.g., 6:00 AM">
                </div>
                <div class="mb-3">
                    <label class="form-label">Description</label>
                    <textarea name="description" class="form-control" rows="2"></textarea>
                </div>
                <button class="btn btn-temple w-100"><i class="fas fa-save"></i> Save</button>
            </form>
        </div>
    </div>
    <div class="col-md-7">
        <div class="content-card">
            <h5><i class="fas fa-om"></i> Daily Pooja Schedule</h5>
            {% for dp in daily_poojas %}
            <div class="pooja-card">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <strong>{{ dp.pooja_name }}</strong>
                        <br><small class="text-muted">{{ dp.description or '' }}</small>
                    </div>
                    <div>
                        <span class="pooja-time me-3">{{ dp.pooja_time or 'TBD' }}</span>
                        <form method="POST" action="{{ url_for('delete_daily_pooja', id=dp.id) }}"
                              style="display:inline">
                            <button class="btn btn-sm btn-danger"><i class="fas fa-trash"></i></button>
                        </form>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
</div>
{% endblock %}
"""

SAMAYA_VAKUPPU_TEMPLATE = """
{% extends "main" %}
{% block content %}
<div class="content-card">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h5 class="mb-0"><i class="fas fa-graduation-cap"></i> Samaya Vakuppu</h5>
        <a href="{{ url_for('add_samaya') }}" class="btn btn-temple">
            <i class="fas fa-plus"></i> Add New
        </a>
    </div>
    <div class="table-responsive">
        <table class="table table-hover data-table">
            <thead>
                <tr><th>#</th><th>Photo</th><th>Student Name</th><th>Father/Mother</th><th>DOB</th>
                    <th>Bond No</th><th>Bank</th><th>Actions</th></tr>
            </thead>
            <tbody>
                {% for s in records %}
                <tr>
                    <td>{{ s.id }}</td>
                    <td>
                        {% if s.photo_filename %}
                        <img src="{{ url_for('uploaded_file', folder='samaya', filename=s.photo_filename) }}"
                             style="width:40px;height:40px;border-radius:50%;object-fit:cover;">
                        {% else %}-{% endif %}
                    </td>
                    <td><strong>{{ s.student_name }}</strong></td>
                    <td>{{ s.father_mother_name or '-' }}</td>
                    <td>{{ s.dob.strftime('%d/%m/%Y') if s.dob else '-' }}</td>
                    <td>{{ s.bond_no or '-' }}</td>
                    <td>{{ s.bond_issuing_bank or '-' }}</td>
                    <td>
                        <a href="{{ url_for('edit_samaya', id=s.id) }}" class="btn btn-sm btn-warning">
                            <i class="fas fa-edit"></i></a>
                        <form method="POST" action="{{ url_for('delete_samaya', id=s.id) }}"
                              style="display:inline" onsubmit="return confirm('Delete?')">
                            <button class="btn btn-sm btn-danger"><i class="fas fa-trash"></i></button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
"""

ADD_SAMAYA_TEMPLATE = """
{% extends "main" %}
{% block content %}
<div class="content-card">
    <h5><i class="fas fa-graduation-cap"></i> {{ 'Edit' if record else 'Add' }} Samaya Vakuppu</h5>
    <form method="POST" enctype="multipart/form-data">
        <div class="row">
            <div class="col-md-4 mb-3">
                <label class="form-label">Student Name *</label>
                <input type="text" name="student_name" class="form-control" required
                       value="{{ record.student_name if record else '' }}">
            </div>
            <div class="col-md-4 mb-3">
                <label class="form-label">Date of Birth</label>
                <input type="date" name="dob" class="form-control"
                       value="{{ record.dob.strftime('%Y-%m-%d') if record and record.dob else '' }}">
            </div>
            <div class="col-md-4 mb-3">
                <label class="form-label">Father/Mother Name</label>
                <input type="text" name="father_mother_name" class="form-control"
                       value="{{ record.father_mother_name if record else '' }}">
            </div>
            <div class="col-md-12 mb-3">
                <label class="form-label">Address</label>
                <textarea name="address" class="form-control" rows="2">{{ record.address if record else '' }}</textarea>
            </div>
            <div class="col-md-4 mb-3">
                <label class="form-label">Bond Issue Date</label>
                <input type="date" name="bond_issue_date" class="form-control"
                       value="{{ record.bond_issue_date.strftime('%Y-%m-%d') if record and record.bond_issue_date else '' }}">
            </div>
            <div class="col-md-4 mb-3">
                <label class="form-label">Bond Issuing Bank</label>
                <input type="text" name="bond_issuing_bank" class="form-control"
                       value="{{ record.bond_issuing_bank if record else '' }}">
            </div>
            <div class="col-md-4 mb-3">
                <label class="form-label">Branch of Bank</label>
                <input type="text" name="branch_of_bank" class="form-control"
                       value="{{ record.branch_of_bank if record else '' }}">
            </div>
            <div class="col-md-4 mb-3">
                <label class="form-label">Bond No</label>
                <input type="text" name="bond_no" class="form-control"
                       value="{{ record.bond_no if record else '' }}">
            </div>
            <div class="col-md-4 mb-3">
                <label class="form-label">Upload Scanned Bond</label>
                <input type="file" name="bond_scan" class="form-control" accept="image/*,.pdf">
                {% if record and record.bond_scan_filename %}
                <small class="text-success">Current: {{ record.bond_scan_filename }}</small>
                {% endif %}
            </div>
            <div class="col-md-4 mb-3">
                <label class="form-label">Upload Photo</label>
                <input type="file" name="photo" class="form-control" accept="image/*">
                {% if record and record.photo_filename %}
                <small class="text-success">Current: {{ record.photo_filename }}</small>
                {% endif %}
            </div>
        </div>
        <div class="text-center">
            <a href="{{ url_for('samaya_vakuppu') }}" class="btn btn-secondary me-2">Cancel</a>
            <button type="submit" class="btn btn-temple"><i class="fas fa-save"></i> Save</button>
        </div>
    </form>
</div>
{% endblock %}
"""

THIRUMANA_MANDAPAM_TEMPLATE = """
{% extends "main" %}
{% block content %}
<div class="content-card">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h5 class="mb-0"><i class="fas fa-building"></i> Thirumana Mandapam</h5>
        <a href="{{ url_for('add_mandapam') }}" class="btn btn-temple">
            <i class="fas fa-plus"></i> Add New
        </a>
    </div>
    <div class="table-responsive">
        <table class="table table-hover data-table">
            <thead>
                <tr><th>#</th><th>Photo</th><th>Name</th><th>Bond No</th><th>Amount</th>
                    <th>No of Bonds</th><th>Issue Date</th><th>Actions</th></tr>
            </thead>
            <tbody>
                {% for m in records %}
                <tr>
                    <td>{{ m.id }}</td>
                    <td>
                        {% if m.photo_filename %}
                        <img src="{{ url_for('uploaded_file', folder='mandapam', filename=m.photo_filename) }}"
                             style="width:40px;height:40px;border-radius:50%;object-fit:cover;">
                        {% else %}-{% endif %}
                    </td>
                    <td><strong>{{ m.name }}</strong></td>
                    <td>{{ m.bond_no or '-' }}</td>
                    <td>₹{{ '{:,.2f}'.format(m.amount) }}</td>
                    <td>{{ m.no_of_bond }}</td>
                    <td>{{ m.bond_issued_date.strftime('%d/%m/%Y') if m.bond_issued_date else '-' }}</td>
                    <td>
                        <a href="{{ url_for('edit_mandapam', id=m.id) }}" class="btn btn-sm btn-warning">
                            <i class="fas fa-edit"></i></a>
                        <form method="POST" action="{{ url_for('delete_mandapam', id=m.id) }}"
                              style="display:inline" onsubmit="return confirm('Delete?')">
                            <button class="btn btn-sm btn-danger"><i class="fas fa-trash"></i></button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
"""

ADD_MANDAPAM_TEMPLATE = """
{% extends "main" %}
{% block content %}
<div class="content-card">
    <h5><i class="fas fa-building"></i> {{ 'Edit' if record else 'Add' }} Thirumana Mandapam</h5>
    <form method="POST" enctype="multipart/form-data">
        <div class="row">
            <div class="col-md-6 mb-3">
                <label class="form-label">Name *</label>
                <input type="text" name="name" class="form-control" required
                       value="{{ record.name if record else '' }}">
            </div>
            <div class="col-md-6 mb-3">
                <label class="form-label">Address</label>
                <textarea name="address" class="form-control" rows="1">{{ record.address if record else '' }}</textarea>
            </div>
            <div class="col-md-3 mb-3">
                <label class="form-label">Bond No</label>
                <input type="text" name="bond_no" class="form-control"
                       value="{{ record.bond_no if record else '' }}">
            </div>
            <div class="col-md-3 mb-3">
                <label class="form-label">Bond Issued Date</label>
                <input type="date" name="bond_issued_date" class="form-control"
                       value="{{ record.bond_issued_date.strftime('%Y-%m-%d') if record and record.bond_issued_date else '' }}">
            </div>
            <div class="col-md-3 mb-3">
                <label class="form-label">Amount</label>
                <input type="number" name="amount" class="form-control" step="0.01"
                       value="{{ record.amount if record else '' }}">
            </div>
            <div class="col-md-3 mb-3">
                <label class="form-label">No of Bonds</label>
                <input type="number" name="no_of_bond" class="form-control"
                       value="{{ record.no_of_bond if record else 1 }}">
            </div>
            <div class="col-md-6 mb-3">
                <label class="form-label">Upload Scan Copy of Bond</label>
                <input type="file" name="bond_scan" class="form-control" accept="image/*,.pdf">
                {% if record and record.bond_scan_filename %}
                <small class="text-success">Current: {{ record.bond_scan_filename }}</small>
                {% endif %}
            </div>
            <div class="col-md-6 mb-3">
                <label class="form-label">Upload Photo</label>
                <input type="file" name="photo" class="form-control" accept="image/*">
                {% if record and record.photo_filename %}
                <small class="text-success">Current: {{ record.photo_filename }}</small>
                {% endif %}
            </div>
        </div>
        <div class="text-center">
            <a href="{{ url_for('thirumana_mandapam') }}" class="btn btn-secondary me-2">Cancel</a>
            <button type="submit" class="btn btn-temple"><i class="fas fa-save"></i> Save</button>
        </div>
    </form>
</div>
{% endblock %}
"""


# ============================================================
# TEMPLATE RENDERING HELPER
# ============================================================

def render(template_str, **kwargs):
    """Render a child template that extends the main template."""
    full_template = template_str
    kwargs['now'] = datetime.now
    return render_template_string(
        MAIN_TEMPLATE.replace('{% block content %}{% endblock %}',
                               '').replace('{% block login_content %}{% endblock %}', '').replace(
            '{% block extra_js %}{% endblock %}', '') if False else full_template,
        **kwargs
    )


# We need a more sophisticated approach for template inheritance with strings
# Let's use Jinja2 environment directly

from jinja2 import Environment, DictLoader

def get_template_env():
    templates = {
        'main': MAIN_TEMPLATE,
        'login': LOGIN_TEMPLATE,
        'dashboard': DASHBOARD_TEMPLATE,
        'devotees': DEVOTEES_TEMPLATE,
        'add_devotee': ADD_DEVOTEE_TEMPLATE,
        'view_devotee': VIEW_DEVOTEE_TEMPLATE,
        'billing': BILLING_TEMPLATE,
        'new_bill': NEW_BILL_TEMPLATE,
        'view_bill': VIEW_BILL_TEMPLATE,
        'expenses': EXPENSES_TEMPLATE,
        'reports': REPORTS_TEMPLATE,
        'settings': SETTINGS_TEMPLATE,
        'user_management': USER_MANAGEMENT_TEMPLATE,
        'daily_pooja': DAILY_POOJA_TEMPLATE,
        'samaya_vakuppu': SAMAYA_VAKUPPU_TEMPLATE,
        'add_samaya': ADD_SAMAYA_TEMPLATE,
        'thirumana_mandapam': THIRUMANA_MANDAPAM_TEMPLATE,
        'add_mandapam': ADD_MANDAPAM_TEMPLATE,
    }
    env = Environment(loader=DictLoader(templates))
    return env

def render_page(template_name, **kwargs):
    env = get_template_env()
    # Add common template functions
    kwargs['current_user'] = current_user
    kwargs['request'] = request
    kwargs['now'] = datetime.now
    kwargs['get_flashed_messages'] = get_flashed_messages_wrapper
    kwargs['url_for'] = url_for
    tmpl = env.get_template(template_name)
    return tmpl.render(**kwargs)

def get_flashed_messages_wrapper(with_categories=False):
    from flask import get_flashed_messages as gfm
    return gfm(with_categories=with_categories)


# ============================================================
# ROUTES
# ============================================================

@app.route('/uploads/<folder>/<filename>')
def uploaded_file(folder, filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], folder, filename)
    if os.path.exists(filepath):
        return send_file(filepath)
    return '', 404


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Welcome back!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid credentials!', 'danger')
    return render_page('login')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/')
@login_required
def dashboard():
    period = request.args.get('period', 'daily')
    today = date.today()

    if period == 'daily':
        start_date = today
        end_date = today
    elif period == 'weekly':
        start_date = today - timedelta(days=today.weekday())
        end_date = today
    elif period == 'monthly':
        start_date = today.replace(day=1)
        end_date = today
    else:  # yearly
        start_date = today.replace(month=1, day=1)
        end_date = today

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    total_income = db.session.query(db.func.sum(Bill.amount)).filter(
        Bill.bill_date >= start_dt, Bill.bill_date <= end_dt, Bill.is_deleted == False
    ).scalar() or 0

    total_expenses = db.session.query(db.func.sum(Expense.amount)).filter(
        Expense.expense_date >= start_date, Expense.expense_date <= end_date
    ).scalar() or 0

    total_devotees = Devotee.query.filter_by(is_family_head=True, is_active=True).count()

    total_bills = Bill.query.filter(
        Bill.bill_date >= start_dt, Bill.bill_date <= end_dt, Bill.is_deleted == False
    ).count()

    # Today's birthdays
    birthdays = Devotee.query.filter(
        db.extract('month', Devotee.dob) == today.month,
        db.extract('day', Devotee.dob) == today.day,
        Devotee.is_active == True
    ).all()

    # Ticker messages
    ticker_messages = []
    for b in birthdays:
        ticker_messages.append(f"Happy Birthday {b.name}! 🎂🎉")

    daily_poojas = DailyPooja.query.filter_by(is_active=True).all()

    recent_bills = Bill.query.filter_by(is_deleted=False).order_by(Bill.bill_date.desc()).limit(10).all()

    return render_page('dashboard',
                       page_title='Dashboard',
                       period=period,
                       total_income=total_income,
                       total_expenses=total_expenses,
                       total_devotees=total_devotees,
                       total_bills=total_bills,
                       birthdays=birthdays,
                       ticker_messages=ticker_messages,
                       daily_poojas=daily_poojas,
                       recent_bills=recent_bills)


# ============================================================
# DEVOTEES
# ============================================================

@app.route('/devotees')
@login_required
def devotees():
    devs = Devotee.query.filter_by(is_family_head=True, is_active=True).order_by(Devotee.name).all()
    return render_page('devotees', page_title='Devotees', devotees=devs)


@app.route('/devotees/add', methods=['GET', 'POST'])
@login_required
def add_devotee():
    pooja_types = PoojaType.query.filter_by(is_active=True).all()
    if request.method == 'POST':
        d = Devotee()
        d.name = request.form.get('name')
        d.dob = datetime.strptime(request.form.get('dob'), '%Y-%m-%d').date() if request.form.get('dob') else None
        d.relation_type = request.form.get('relation_type')
        d.mobile_no = request.form.get('mobile_no')
        d.whatsapp_no = request.form.get('whatsapp_no')
        d.wedding_day = datetime.strptime(request.form.get('wedding_day'), '%Y-%m-%d').date() if request.form.get('wedding_day') else None
        d.natchathiram = request.form.get('natchathiram')
        d.address = request.form.get('address')
        d.is_family_head = True

        # Photo
        photo = request.files.get('photo')
        if photo and photo.filename:
            fname = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{photo.filename}")
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], 'devotees', fname))
            d.photo_filename = fname

        db.session.add(d)
        db.session.flush()

        # Yearly Poojas
        yp_types = request.form.getlist('yp_pooja_type[]')
        yp_names = request.form.getlist('yp_pooja_name[]')
        yp_dates = request.form.getlist('yp_pooja_date[]')
        yp_notes = request.form.getlist('yp_notes[]')
        for i in range(len(yp_types)):
            if yp_types[i] or yp_names[i]:
                yp = DevoteeYearlyPooja()
                yp.devotee_id = d.id
                yp.pooja_type_id = int(yp_types[i]) if yp_types[i] else None
                yp.pooja_name = yp_names[i] if i < len(yp_names) else ''
                yp.pooja_date = datetime.strptime(yp_dates[i], '%Y-%m-%d').date() if i < len(yp_dates) and yp_dates[i] else None
                yp.notes = yp_notes[i] if i < len(yp_notes) else ''
                db.session.add(yp)

        # Family Members
        fm_names = request.form.getlist('fm_name[]')
        fm_dobs = request.form.getlist('fm_dob[]')
        fm_relations = request.form.getlist('fm_relation[]')
        fm_weddings = request.form.getlist('fm_wedding[]')
        fm_natchathirams = request.form.getlist('fm_natchathiram[]')
        for i in range(len(fm_names)):
            if fm_names[i]:
                fm = Devotee()
                fm.name = fm_names[i]
                fm.dob = datetime.strptime(fm_dobs[i], '%Y-%m-%d').date() if i < len(fm_dobs) and fm_dobs[i] else None
                fm.relation_type = fm_relations[i] if i < len(fm_relations) else ''
                fm.wedding_day = datetime.strptime(fm_weddings[i], '%Y-%m-%d').date() if i < len(fm_weddings) and fm_weddings[i] else None
                fm.natchathiram = fm_natchathirams[i] if i < len(fm_natchathirams) else ''
                fm.is_family_head = False
                fm.family_head_id = d.id
                fm.address = d.address
                db.session.add(fm)

        db.session.commit()
        flash('Devotee added successfully!', 'success')
        return redirect(url_for('devotees'))

    return render_page('add_devotee', page_title='Add Devotee',
                       devotee=None,
                       natchathiram_list=NATCHATHIRAM_LIST,
                       relation_types=RELATION_TYPES,
                       pooja_types=pooja_types)


@app.route('/devotees/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_devotee(id):
    d = Devotee.query.get_or_404(id)
    pooja_types = PoojaType.query.filter_by(is_active=True).all()

    if request.method == 'POST':
        d.name = request.form.get('name')
        d.dob = datetime.strptime(request.form.get('dob'), '%Y-%m-%d').date() if request.form.get('dob') else None
        d.relation_type = request.form.get('relation_type')
        d.mobile_no = request.form.get('mobile_no')
        d.whatsapp_no = request.form.get('whatsapp_no')
        d.wedding_day = datetime.strptime(request.form.get('wedding_day'), '%Y-%m-%d').date() if request.form.get('wedding_day') else None
        d.natchathiram = request.form.get('natchathiram')
        d.address = request.form.get('address')

        photo = request.files.get('photo')
        if photo and photo.filename:
            fname = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{photo.filename}")
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], 'devotees', fname))
            d.photo_filename = fname

        # Update Yearly Poojas - delete old, add new
        DevoteeYearlyPooja.query.filter_by(devotee_id=d.id).delete()
        yp_types = request.form.getlist('yp_pooja_type[]')
        yp_names = request.form.getlist('yp_pooja_name[]')
        yp_dates = request.form.getlist('yp_pooja_date[]')
        yp_notes = request.form.getlist('yp_notes[]')
        for i in range(len(yp_types)):
            if yp_types[i] or (i < len(yp_names) and yp_names[i]):
                yp = DevoteeYearlyPooja()
                yp.devotee_id = d.id
                yp.pooja_type_id = int(yp_types[i]) if yp_types[i] else None
                yp.pooja_name = yp_names[i] if i < len(yp_names) else ''
                yp.pooja_date = datetime.strptime(yp_dates[i], '%Y-%m-%d').date() if i < len(yp_dates) and yp_dates[i] else None
                yp.notes = yp_notes[i] if i < len(yp_notes) else ''
                db.session.add(yp)

        # Update Family Members - delete old members not in form, update/add
        existing_fm_ids = [fm.id for fm in d.family_members.all()]
        submitted_fm_ids = request.form.getlist('fm_id[]')
        submitted_fm_ids_int = [int(x) for x in submitted_fm_ids if x and x != '0']

        # Delete removed members
        for eid in existing_fm_ids:
            if eid not in submitted_fm_ids_int:
                Devotee.query.filter_by(id=eid).delete()

        fm_names = request.form.getlist('fm_name[]')
        fm_dobs = request.form.getlist('fm_dob[]')
        fm_relations = request.form.getlist('fm_relation[]')
        fm_weddings = request.form.getlist('fm_wedding[]')
        fm_natchathirams = request.form.getlist('fm_natchathiram[]')

        for i in range(len(fm_names)):
            if not fm_names[i]:
                continue
            fm_id = int(submitted_fm_ids[i]) if i < len(submitted_fm_ids) and submitted_fm_ids[i] != '0' else 0
            if fm_id:
                fm = Devotee.query.get(fm_id)
                if not fm:
                    fm = Devotee()
                    fm.family_head_id = d.id
                    fm.is_family_head = False
                    db.session.add(fm)
            else:
                fm = Devotee()
                fm.family_head_id = d.id
                fm.is_family_head = False
                db.session.add(fm)

            fm.name = fm_names[i]
            fm.dob = datetime.strptime(fm_dobs[i], '%Y-%m-%d').date() if i < len(fm_dobs) and fm_dobs[i] else None
            fm.relation_type = fm_relations[i] if i < len(fm_relations) else ''
            fm.wedding_day = datetime.strptime(fm_weddings[i], '%Y-%m-%d').date() if i < len(fm_weddings) and fm_weddings[i] else None
            fm.natchathiram = fm_natchathirams[i] if i < len(fm_natchathirams) else ''
            fm.address = d.address

        db.session.commit()
        flash('Devotee updated successfully!', 'success')
        return redirect(url_for('devotees'))

    return render_page('add_devotee', page_title='Edit Devotee',
                       devotee=d,
                       natchathiram_list=NATCHATHIRAM_LIST,
                       relation_types=RELATION_TYPES,
                       pooja_types=pooja_types)


@app.route('/devotees/view/<int:id>')
@login_required
def view_devotee(id):
    d = Devotee.query.get_or_404(id)
    return render_page('view_devotee', page_title='View Devotee', devotee=d)


@app.route('/devotees/delete/<int:id>', methods=['POST'])
@login_required
def delete_devotee(id):
    d = Devotee.query.get_or_404(id)
    # Delete family members
    Devotee.query.filter_by(family_head_id=d.id).delete()
    DevoteeYearlyPooja.query.filter_by(devotee_id=d.id).delete()
    db.session.delete(d)
    db.session.commit()
    flash('Devotee deleted!', 'success')
    return redirect(url_for('devotees'))


# ============================================================
# BILLING
# ============================================================

@app.route('/billing')
@login_required
def billing():
    bills = Bill.query.order_by(Bill.bill_date.desc()).all()
    return render_page('billing', page_title='Billing', bills=bills)


@app.route('/billing/new', methods=['GET', 'POST'])
@login_required
def new_bill():
    pooja_types = PoojaType.query.filter_by(is_active=True).all()
    if request.method == 'POST':
        bill = Bill()
        bill.bill_number = f"B{datetime.now().strftime('%Y%m%d%H%M%S')}"
        bill.manual_bill_no = request.form.get('manual_bill_no')
        bill.bill_book_no = request.form.get('bill_book_no')
        bill.devotee_type = request.form.get('devotee_type')
        bill.pooja_type_id = int(request.form.get('pooja_type_id')) if request.form.get('pooja_type_id') else None
        bill.amount = float(request.form.get('amount', 0))
        bill.notes = request.form.get('notes')
        bill.created_by = current_user.id

        if bill.devotee_type == 'enrolled':
            bill.devotee_id = int(request.form.get('devotee_id')) if request.form.get('devotee_id') else None
        else:
            bill.guest_name = request.form.get('guest_name')
            bill.guest_address = request.form.get('guest_address')
            bill.guest_mobile = request.form.get('guest_mobile')
            bill.guest_whatsapp = request.form.get('guest_whatsapp')

        db.session.add(bill)
        db.session.commit()
        flash('Bill generated successfully!', 'success')
        return redirect(url_for('view_bill', id=bill.id))

    return render_page('new_bill', page_title='New Bill', pooja_types=pooja_types)


@app.route('/billing/view/<int:id>')
@login_required
def view_bill(id):
    bill = Bill.query.get_or_404(id)
    return render_page('view_bill', page_title='View Bill', bill=bill)


@app.route('/billing/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_bill(id):
    bill = Bill.query.get_or_404(id)
    bill.is_deleted = True
    bill.deleted_by = current_user.id
    bill.deleted_at = datetime.utcnow()
    db.session.commit()
    flash('Bill deleted!', 'success')
    return redirect(url_for('billing'))


@app.route('/api/search_devotees')
@login_required
def api_search_devotees():
    q = request.args.get('q', '')
    devotees = Devotee.query.filter(
        Devotee.is_family_head == True,
        Devotee.is_active == True,
        db.or_(
            Devotee.name.ilike(f'%{q}%'),
            Devotee.mobile_no.ilike(f'%{q}%'),
            Devotee.whatsapp_no.ilike(f'%{q}%'),
            Devotee.address.ilike(f'%{q}%')
        )
    ).limit(20).all()
    result = [{'id': d.id, 'name': d.name, 'mobile': d.mobile_no or '',
               'address': d.address or '', 'whatsapp': d.whatsapp_no or ''} for d in devotees]
    return jsonify(result)


# ============================================================
# EXPENSES
# ============================================================

@app.route('/expenses', methods=['GET', 'POST'])
@login_required
def expenses_page():
    expense_types = ExpenseType.query.filter_by(is_active=True).all()
    if request.method == 'POST':
        exp = Expense()
        exp.expense_type_id = int(request.form.get('expense_type_id'))
        exp.amount = float(request.form.get('amount', 0))
        exp.description = request.form.get('description')
        exp.expense_date = datetime.strptime(request.form.get('expense_date'), '%Y-%m-%d').date() if request.form.get('expense_date') else date.today()
        exp.created_by = current_user.id
        db.session.add(exp)
        db.session.commit()
        flash('Expense added!', 'success')
        return redirect(url_for('expenses_page'))

    expenses = Expense.query.order_by(Expense.expense_date.desc()).all()
    return render_page('expenses', page_title='Expenses',
                       expense_types=expense_types,
                       expenses=expenses,
                       today=date.today().strftime('%Y-%m-%d'))


@app.route('/expenses/delete/<int:id>', methods=['POST'])
@login_required
def delete_expense(id):
    exp = Expense.query.get_or_404(id)
    db.session.delete(exp)
    db.session.commit()
    flash('Expense deleted!', 'success')
    return redirect(url_for('expenses_page'))


# ============================================================
# REPORTS
# ============================================================

@app.route('/reports')
@login_required
def reports():
    period = request.args.get('period', 'daily')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    pooja_type_filter = request.args.get('pooja_type_id', '')
    today = date.today()

    if period == 'daily':
        start_date = today
        end_date = today
    elif period == 'weekly':
        start_date = today - timedelta(days=today.weekday())
        end_date = today
    elif period == 'monthly':
        start_date = today.replace(day=1)
        end_date = today
    elif period == 'yearly':
        start_date = today.replace(month=1, day=1)
        end_date = today
    elif period == 'custom' and date_from and date_to:
        start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
        end_date = datetime.strptime(date_to, '%Y-%m-%d').date()
    else:
        start_date = today
        end_date = today

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    bills_query = Bill.query.filter(
        Bill.bill_date >= start_dt, Bill.bill_date <= end_dt, Bill.is_deleted == False
    )
    if pooja_type_filter:
        bills_query = bills_query.filter(Bill.pooja_type_id == int(pooja_type_filter))

    bills = bills_query.order_by(Bill.bill_date.desc()).all()
    total_income = sum(b.amount for b in bills)

    expenses = Expense.query.filter(
        Expense.expense_date >= start_date, Expense.expense_date <= end_date
    ).order_by(Expense.expense_date.desc()).all()
    total_expenses = sum(e.amount for e in expenses)

    pooja_types = PoojaType.query.filter_by(is_active=True).all()

    return render_page('reports', page_title='Reports',
                       period=period,
                       date_from=date_from,
                       date_to=date_to,
                       pooja_type_filter=pooja_type_filter,
                       bills=bills,
                       expenses=expenses,
                       total_income=total_income,
                       total_expenses=total_expenses,
                       pooja_types=pooja_types)


# ============================================================
# SETTINGS
# ============================================================

@app.route('/settings')
@login_required
def settings():
    pooja_types = PoojaType.query.filter_by(is_active=True).all()
    expense_types = ExpenseType.query.filter_by(is_active=True).all()
    return render_page('settings', page_title='Settings',
                       pooja_types=pooja_types,
                       expense_types=expense_types)


@app.route('/settings/pooja_type/add', methods=['POST'])
@login_required
def add_pooja_type():
    pt = PoojaType()
    pt.name = request.form.get('name')
    pt.amount = float(request.form.get('amount', 0))
    db.session.add(pt)
    db.session.commit()
    flash('Pooja type added!', 'success')
    return redirect(url_for('settings'))


@app.route('/settings/pooja_type/delete/<int:id>', methods=['POST'])
@login_required
def delete_pooja_type(id):
    pt = PoojaType.query.get_or_404(id)
    pt.is_active = False
    db.session.commit()
    flash('Pooja type removed!', 'success')
    return redirect(url_for('settings'))


@app.route('/settings/expense_type/add', methods=['POST'])
@login_required
def add_expense_type():
    et = ExpenseType()
    et.name = request.form.get('name')
    db.session.add(et)
    db.session.commit()
    flash('Expense type added!', 'success')
    return redirect(url_for('settings'))


@app.route('/settings/expense_type/delete/<int:id>', methods=['POST'])
@login_required
def delete_expense_type(id):
    et = ExpenseType.query.get_or_404(id)
    et.is_active = False
    db.session.commit()
    flash('Expense type removed!', 'success')
    return redirect(url_for('settings'))


# ============================================================
# USER MANAGEMENT
# ============================================================

@app.route('/users', methods=['GET', 'POST'])
@login_required
@admin_required
def user_management():
    if request.method == 'POST':
        username = request.form.get('username')
        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'danger')
        else:
            user = User()
            user.username = username
            user.full_name = request.form.get('full_name')
            user.set_password(request.form.get('password'))
            user.role = request.form.get('role', 'user')
            db.session.add(user)
            db.session.commit()
            flash('User created!', 'success')
        return redirect(url_for('user_management'))

    users = User.query.all()
    return render_page('user_management', page_title='User Management', users=users)


@app.route('/users/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_user(id):
    user = User.query.get_or_404(id)
    if user.username == 'admin':
        flash('Cannot delete admin user!', 'danger')
    else:
        db.session.delete(user)
        db.session.commit()
        flash('User deleted!', 'success')
    return redirect(url_for('user_management'))


# ============================================================
# DAILY POOJA
# ============================================================

@app.route('/daily-pooja', methods=['GET', 'POST'])
@login_required
def daily_pooja_page():
    if request.method == 'POST':
        dp = DailyPooja()
        dp.pooja_name = request.form.get('pooja_name')
        dp.pooja_time = request.form.get('pooja_time')
        dp.description = request.form.get('description')
        db.session.add(dp)
        db.session.commit()
        flash('Daily pooja added!', 'success')
        return redirect(url_for('daily_pooja_page'))

    daily_poojas = DailyPooja.query.filter_by(is_active=True).all()
    return render_page('daily_pooja', page_title='Daily Pooja', daily_poojas=daily_poojas)


@app.route('/daily-pooja/delete/<int:id>', methods=['POST'])
@login_required
def delete_daily_pooja(id):
    dp = DailyPooja.query.get_or_404(id)
    dp.is_active = False
    db.session.commit()
    flash('Daily pooja removed!', 'success')
    return redirect(url_for('daily_pooja_page'))


# ============================================================
# SAMAYA VAKUPPU
# ============================================================

@app.route('/samaya-vakuppu')
@login_required
def samaya_vakuppu():
    records = SamayaVakuppu.query.order_by(SamayaVakuppu.created_at.desc()).all()
    return render_page('samaya_vakuppu', page_title='Samaya Vakuppu', records=records)


@app.route('/samaya-vakuppu/add', methods=['GET', 'POST'])
@login_required
def add_samaya():
    if request.method == 'POST':
        s = SamayaVakuppu()
        s.student_name = request.form.get('student_name')
        s.dob = datetime.strptime(request.form.get('dob'), '%Y-%m-%d').date() if request.form.get('dob') else None
        s.address = request.form.get('address')
        s.father_mother_name = request.form.get('father_mother_name')
        s.bond_issue_date = datetime.strptime(request.form.get('bond_issue_date'), '%Y-%m-%d').date() if request.form.get('bond_issue_date') else None
        s.bond_issuing_bank = request.form.get('bond_issuing_bank')
        s.branch_of_bank = request.form.get('branch_of_bank')
        s.bond_no = request.form.get('bond_no')

        bond_scan = request.files.get('bond_scan')
        if bond_scan and bond_scan.filename:
            fname = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_bond_{bond_scan.filename}")
            bond_scan.save(os.path.join(app.config['UPLOAD_FOLDER'], 'samaya', fname))
            s.bond_scan_filename = fname

        photo = request.files.get('photo')
        if photo and photo.filename:
            fname = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_photo_{photo.filename}")
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], 'samaya', fname))
            s.photo_filename = fname

        db.session.add(s)
        db.session.commit()
        flash('Record added!', 'success')
        return redirect(url_for('samaya_vakuppu'))

    return render_page('add_samaya', page_title='Add Samaya Vakuppu', record=None)


@app.route('/samaya-vakuppu/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_samaya(id):
    s = SamayaVakuppu.query.get_or_404(id)
    if request.method == 'POST':
        s.student_name = request.form.get('student_name')
        s.dob = datetime.strptime(request.form.get('dob'), '%Y-%m-%d').date() if request.form.get('dob') else None
        s.address = request.form.get('address')
        s.father_mother_name = request.form.get('father_mother_name')
        s.bond_issue_date = datetime.strptime(request.form.get('bond_issue_date'), '%Y-%m-%d').date() if request.form.get('bond_issue_date') else None
        s.bond_issuing_bank = request.form.get('bond_issuing_bank')
        s.branch_of_bank = request.form.get('branch_of_bank')
        s.bond_no = request.form.get('bond_no')

        bond_scan = request.files.get('bond_scan')
        if bond_scan and bond_scan.filename:
            fname = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_bond_{bond_scan.filename}")
            bond_scan.save(os.path.join(app.config['UPLOAD_FOLDER'], 'samaya', fname))
            s.bond_scan_filename = fname

        photo = request.files.get('photo')
        if photo and photo.filename:
            fname = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_photo_{photo.filename}")
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], 'samaya', fname))
            s.photo_filename = fname

        db.session.commit()
        flash('Record updated!', 'success')
        return redirect(url_for('samaya_vakuppu'))

    return render_page('add_samaya', page_title='Edit Samaya Vakuppu', record=s)


@app.route('/samaya-vakuppu/delete/<int:id>', methods=['POST'])
@login_required
def delete_samaya(id):
    s = SamayaVakuppu.query.get_or_404(id)
    db.session.delete(s)
    db.session.commit()
    flash('Record deleted!', 'success')
    return redirect(url_for('samaya_vakuppu'))


# ============================================================
# THIRUMANA MANDAPAM
# ============================================================

@app.route('/thirumana-mandapam')
@login_required
def thirumana_mandapam():
    records = ThirumanaMandapam.query.order_by(ThirumanaMandapam.created_at.desc()).all()
    return render_page('thirumana_mandapam', page_title='Thirumana Mandapam', records=records)


@app.route('/thirumana-mandapam/add', methods=['GET', 'POST'])
@login_required
def add_mandapam():
    if request.method == 'POST':
        m = ThirumanaMandapam()
        m.name = request.form.get('name')
        m.address = request.form.get('address')
        m.bond_no = request.form.get('bond_no')
        m.bond_issued_date = datetime.strptime(request.form.get('bond_issued_date'), '%Y-%m-%d').date() if request.form.get('bond_issued_date') else None
        m.amount = float(request.form.get('amount', 0))
        m.no_of_bond = int(request.form.get('no_of_bond', 1))

        bond_scan = request.files.get('bond_scan')
        if bond_scan and bond_scan.filename:
            fname = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_bond_{bond_scan.filename}")
            bond_scan.save(os.path.join(app.config['UPLOAD_FOLDER'], 'mandapam', fname))
            m.bond_scan_filename = fname

        photo = request.files.get('photo')
        if photo and photo.filename:
            fname = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_photo_{photo.filename}")
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], 'mandapam', fname))
            m.photo_filename = fname

        db.session.add(m)
        db.session.commit()
        flash('Record added!', 'success')
        return redirect(url_for('thirumana_mandapam'))

    return render_page('add_mandapam', page_title='Add Thirumana Mandapam', record=None)


@app.route('/thirumana-mandapam/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_mandapam(id):
    m = ThirumanaMandapam.query.get_or_404(id)
    if request.method == 'POST':
        m.name = request.form.get('name')
        m.address = request.form.get('address')
        m.bond_no = request.form.get('bond_no')
        m.bond_issued_date = datetime.strptime(request.form.get('bond_issued_date'), '%Y-%m-%d').date() if request.form.get('bond_issued_date') else None
        m.amount = float(request.form.get('amount', 0))
        m.no_of_bond = int(request.form.get('no_of_bond', 1))

        bond_scan = request.files.get('bond_scan')
        if bond_scan and bond_scan.filename:
            fname = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_bond_{bond_scan.filename}")
            bond_scan.save(os.path.join(app.config['UPLOAD_FOLDER'], 'mandapam', fname))
            m.bond_scan_filename = fname

        photo = request.files.get('photo')
        if photo and photo.filename:
            fname = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_photo_{photo.filename}")
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], 'mandapam', fname))
            m.photo_filename = fname

        db.session.commit()
        flash('Record updated!', 'success')
        return redirect(url_for('thirumana_mandapam'))

    return render_page('add_mandapam', page_title='Edit Thirumana Mandapam', record=m)


@app.route('/thirumana-mandapam/delete/<int:id>', methods=['POST'])
@login_required
def delete_mandapam(id):
    m = ThirumanaMandapam.query.get_or_404(id)
    db.session.delete(m)
    db.session.commit()
    flash('Record deleted!', 'success')
    return redirect(url_for('thirumana_mandapam'))


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_db():
    """Initialize database and create default admin user."""
    with app.app_context():
        db.create_all()

        # Create default admin
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User()
            admin.username = 'admin'
            admin.full_name = 'Administrator'
            admin.set_password('admin123')
            admin.role = 'admin'
            db.session.add(admin)

            # Add default pooja types
            default_poojas = [
                ('அர்ச்சனை (Archana)', 20),
                ('அபிஷேகம் (Abhishekam)', 50),
                ('சஹஸ்ரநாம அர்ச்சனை (Sahasranama)', 100),
                ('ஹோமம் (Homam)', 500),
                ('சிறப்பு பூஜை (Special Pooja)', 200),
                ('நவக்கிரக பூஜை (Navagraha Pooja)', 150),
                ('சந்தன கவசம் (Sandana Kavasam)', 75),
                ('தீபாராதனை (Deeparadhanai)', 25),
            ]
            for name, amt in default_poojas:
                pt = PoojaType(name=name, amount=amt)
                db.session.add(pt)

            # Add default expense types
            default_expenses = [
                'பூ (Flowers)', 'விளக்கு எண்ணெய் (Lamp Oil)',
                'பிரசாதம் (Prasadam)', 'மின்சாரம் (Electricity)',
                'பராமரிப்பு (Maintenance)', 'ஊழியர் சம்பளம் (Staff Salary)',
                'பிற செலவுகள் (Other Expenses)'
            ]
            for name in default_expenses:
                et = ExpenseType(name=name)
                db.session.add(et)

            # Add default daily pooja schedule
            default_daily = [
                ('காலை திருவிழா (Morning Pooja)', '6:00 AM', 'Suprabatham and morning rituals'),
                ('உச்சிக்கால பூஜை (Afternoon Pooja)', '12:00 PM', 'Uchikala pooja'),
                ('மாலை பூஜை (Evening Pooja)', '6:00 PM', 'Sayaratchai pooja'),
                ('இரவு பூஜை (Night Pooja)', '8:00 PM', 'Arthajama pooja'),
            ]
            for name, time, desc in default_daily:
                dp = DailyPooja(pooja_name=name, pooja_time=time, description=desc)
                db.session.add(dp)

            db.session.commit()
            print("✅ Database initialized with default data!")
            print("📝 Default Login -> Username: admin | Password: admin123")


# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    init_db()
    print("\n" + "="*60)
    print("🕉️  TEMPLE MANAGEMENT SYSTEM")
    print("="*60)
    print("🌐 Open browser: http://localhost:5000")
    print("👤 Username: admin")
    print("🔑 Password: admin123")
    print("="*60 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
