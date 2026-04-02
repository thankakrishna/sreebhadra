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

# Temple Configuration
TEMPLE_NAME = "Arulmigu Bhadreshwari Amman Kovil"
TEMPLE_TRUST = "Samrakshana Seva Trust"
TEMPLE_REG = "179/2004"
TEMPLE_PLACE = "Kanjampuram"
TEMPLE_DISTRICT = "Kanniyakumari Dist- 629154"
TEMPLE_ADDRESS_LINE1 = f"{TEMPLE_NAME}"
TEMPLE_ADDRESS_LINE2 = f"{TEMPLE_TRUST} - {TEMPLE_REG}"
TEMPLE_ADDRESS_LINE3 = f"{TEMPLE_PLACE}, {TEMPLE_DISTRICT}"
TEMPLE_FULL_ADDRESS = f"{TEMPLE_ADDRESS_LINE1}, {TEMPLE_ADDRESS_LINE2}, {TEMPLE_ADDRESS_LINE3}"

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'devotees'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'samaya'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'mandapam'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'temple'), exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ============================================================
# AMMAN IMAGE PLACEHOLDER (SVG)
# Place your actual amman.png / amman.jpg in uploads/temple/ folder
# Place your temple_bg.jpg in uploads/temple/ folder for login background
# ============================================================
AMMAN_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
<defs><radialGradient id="g1" cx="50%%" cy="50%%" r="50%%">
<stop offset="0%%" style="stop-color:#FFD700;stop-opacity:0.4"/>
<stop offset="100%%" style="stop-color:#FF6600;stop-opacity:0"/>
</radialGradient></defs>
<circle cx="100" cy="100" r="98" fill="#FFF8DC" stroke="#FFD700" stroke-width="3"/>
<circle cx="100" cy="100" r="92" fill="url(#g1)" stroke="#8B0000" stroke-width="1.5"/>
<text x="100" y="65" text-anchor="middle" font-size="35">🙏</text>
<text x="100" y="95" text-anchor="middle" font-size="11" fill="#8B0000" font-weight="bold">ஸ்ரீ பத்ரேஸ்வரி</text>
<text x="100" y="112" text-anchor="middle" font-size="11" fill="#8B0000" font-weight="bold">அம்மன்</text>
<text x="100" y="135" text-anchor="middle" font-size="9" fill="#DC143C">Bhadreshwari</text>
<text x="100" y="148" text-anchor="middle" font-size="9" fill="#DC143C">Amman</text>
<text x="100" y="175" text-anchor="middle" font-size="22">🪷</text>
</svg>'''

AMMAN_B64 = base64.b64encode(AMMAN_SVG.encode()).decode()
AMMAN_DATA_URI = f"data:image/svg+xml;base64,{AMMAN_B64}"


def get_amman_image():
    for ext, mime in [('png','png'),('jpg','jpeg'),('jpeg','jpeg'),('webp','webp')]:
        p = os.path.join(app.config['UPLOAD_FOLDER'], 'temple', f'amman.{ext}')
        if os.path.exists(p):
            with open(p, 'rb') as f:
                return f"data:image/{mime};base64,{base64.b64encode(f.read()).decode()}"
    return AMMAN_DATA_URI


def get_temple_bg():
    for ext, mime in [('jpg','jpeg'),('jpeg','jpeg'),('png','png'),('webp','webp')]:
        p = os.path.join(app.config['UPLOAD_FOLDER'], 'temple', f'temple_bg.{ext}')
        if os.path.exists(p):
            with open(p, 'rb') as f:
                return f"data:image/{mime};base64,{base64.b64encode(f.read()).decode()}"
    return None


# ============================================================
# DATABASE MODELS
# ============================================================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(150))
    role = db.Column(db.String(20), default='user')
    is_active_user = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    def set_password(self, pw): self.password_hash = generate_password_hash(pw)
    def check_password(self, pw): return check_password_hash(self.password_hash, pw)

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
    family_members = db.relationship('Devotee', backref=db.backref('family_head_ref', remote_side=[id]), lazy='dynamic')
    yearly_poojas = db.relationship('DevoteeYearlyPooja', backref='devotee', lazy='dynamic', cascade='all, delete-orphan')

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
    devotee_type = db.Column(db.String(20))
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
    delete_reason = db.Column(db.Text, nullable=True)
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
# LOGIN MANAGER & DECORATORS
# ============================================================
@login_manager.user_loader
def load_user(uid): return User.query.get(int(uid))

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Admin access required!', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated


# ============================================================
# LISTS
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
    'Self','Spouse','Son','Daughter','Father','Mother','Brother','Sister',
    'Grandfather','Grandmother','Father-in-law','Mother-in-law',
    'Son-in-law','Daughter-in-law','Uncle','Aunt','Nephew','Niece','Cousin','Other'
]


# ============================================================
# CONTEXT PROCESSOR
# ============================================================
@app.context_processor
def inject_globals():
    return {
        'now': datetime.utcnow,
        'temple_name': TEMPLE_NAME,
        'temple_trust': TEMPLE_TRUST,
        'temple_address_line1': TEMPLE_ADDRESS_LINE1,
        'temple_address_line2': TEMPLE_ADDRESS_LINE2,
        'temple_address_line3': TEMPLE_ADDRESS_LINE3,
        'temple_full_address': TEMPLE_FULL_ADDRESS,
        'amman_image': get_amman_image(),
        'temple_bg': get_temple_bg(),
    }


# ============================================================
# JINJA TEMPLATE LOADER
# ============================================================
from jinja2 import BaseLoader, TemplateNotFound

class DictLoader(BaseLoader):
    def __init__(self, mapping):
        self.mapping = mapping
    def get_source(self, environment, template):
        if template in self.mapping:
            source = self.mapping[template]
            return source, template, lambda: True
        raise TemplateNotFound(template)


# ============================================================
# ALL TEMPLATES
# ============================================================

MAIN_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🕉️ {{ temple_name }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <link href="https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css" rel="stylesheet">
    <style>
        :root { --td: #8B0000; --tg: #FFD700; --tl: #FFF8DC; }
        * { margin:0; padding:0; box-sizing:border-box; }
        body { font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif; background:linear-gradient(135deg,#FFF8DC 0%,#FFEFD5 50%,#FFE4B5 100%); min-height:100vh; }
        .sidebar { position:fixed; top:0; left:0; width:270px; height:100vh; background:linear-gradient(180deg,#8B0000 0%,#B22222 50%,#DC143C 100%); color:white; z-index:1000; overflow-y:auto; transition:all 0.3s; box-shadow:4px 0 15px rgba(0,0,0,0.3); }
        .sidebar-header { padding:18px 12px; text-align:center; border-bottom:2px solid rgba(255,215,0,0.3); background:rgba(0,0,0,0.2); }
        .amman-round { width:80px; height:80px; border-radius:50%; border:3px solid #FFD700; object-fit:cover; box-shadow:0 0 20px rgba(255,215,0,0.5); display:block; margin:0 auto 8px; background:#FFF8DC; }
        .sidebar-header h4 { color:#FFD700; font-size:0.88em; margin:3px 0; line-height:1.3; }
        .sidebar-header .addr { color:rgba(255,215,0,0.7); font-size:0.68em; }
        .sidebar-menu { padding:8px 0; }
        .sidebar-menu a { display:flex; align-items:center; padding:11px 18px; color:#FFF8DC; text-decoration:none; transition:all 0.3s; border-left:3px solid transparent; font-size:0.9em; }
        .sidebar-menu a:hover,.sidebar-menu a.active { background:rgba(255,215,0,0.15); border-left:3px solid #FFD700; color:#FFD700; }
        .sidebar-menu a i { width:28px; text-align:center; margin-right:10px; }
        .sidebar-menu .divider { border-top:1px solid rgba(255,215,0,0.2); margin:6px 18px; }
        .main-content { margin-left:270px; padding:18px; min-height:100vh; }
        .top-bar { background:white; border-radius:12px; padding:12px 22px; margin-bottom:18px; box-shadow:0 2px 10px rgba(0,0,0,0.08); display:flex; justify-content:space-between; align-items:center; }
        .top-bar .amman-sm { width:32px; height:32px; border-radius:50%; border:2px solid #FFD700; object-fit:cover; vertical-align:middle; margin-right:8px; }
        .news-ticker-container { background:linear-gradient(90deg,#8B0000,#DC143C,#8B0000); border-radius:10px; padding:10px 15px; margin-bottom:18px; overflow:hidden; }
        .news-ticker { display:flex; animation:ticker 30s linear infinite; white-space:nowrap; }
        .news-ticker span { color:#FFD700; padding:0 50px; font-weight:500; }
        @keyframes ticker { 0%{transform:translateX(100%);} 100%{transform:translateX(-100%);} }
        .stat-card { border-radius:15px; padding:22px; color:white; box-shadow:0 5px 20px rgba(0,0,0,0.15); transition:transform 0.3s; position:relative; overflow:hidden; }
        .stat-card:hover { transform:translateY(-5px); }
        .stat-card.income { background:linear-gradient(135deg,#228B22,#32CD32); }
        .stat-card.expense { background:linear-gradient(135deg,#DC143C,#FF4500); }
        .stat-card.devotees { background:linear-gradient(135deg,#4169E1,#6495ED); }
        .stat-card.bills { background:linear-gradient(135deg,#FF8C00,#FFD700); }
        .stat-card h6 { font-size:0.83em; opacity:0.9; margin-bottom:4px; }
        .stat-card h3 { font-size:1.7em; font-weight:700; }
        .stat-card .si { font-size:2.8em; opacity:0.25; position:absolute; right:18px; top:18px; }
        .content-card { background:white; border-radius:12px; box-shadow:0 2px 15px rgba(0,0,0,0.08); padding:22px; margin-bottom:18px; }
        .content-card h5 { color:#8B0000; border-bottom:2px solid #FFD700; padding-bottom:8px; margin-bottom:18px; font-weight:600; }
        .btn-temple { background:linear-gradient(135deg,#8B0000,#DC143C); color:white; border:none; padding:9px 22px; border-radius:8px; font-weight:500; transition:all 0.3s; }
        .btn-temple:hover { background:linear-gradient(135deg,#DC143C,#FF4500); color:white; transform:translateY(-2px); box-shadow:0 4px 12px rgba(220,20,60,0.4); }
        .btn-gold { background:linear-gradient(135deg,#DAA520,#FFD700); color:#8B0000; border:none; padding:9px 22px; border-radius:8px; font-weight:600; }
        .btn-gold:hover { background:linear-gradient(135deg,#FFD700,#FFA500); color:#8B0000; }
        .form-control:focus,.form-select:focus { border-color:#DC143C; box-shadow:0 0 0 0.2rem rgba(220,20,60,0.25); }
        .form-label { font-weight:600; color:#555; font-size:0.88em; }
        .table thead { background:linear-gradient(135deg,#8B0000,#DC143C); color:white; }
        .table thead th { font-weight:600; border:none; padding:10px; }
        .pooja-card { background:linear-gradient(135deg,#FFF8DC,#FFEFD5); border:1px solid #FFD700; border-radius:10px; padding:12px; margin-bottom:8px; border-left:4px solid #8B0000; }
        .pooja-time { color:#8B0000; font-weight:700; }
        .period-btn { border:2px solid #8B0000; color:#8B0000; background:white; padding:7px 18px; border-radius:25px; font-weight:600; margin:0 2px; transition:all 0.3s; }
        .period-btn:hover,.period-btn.active { background:#8B0000; color:#FFD700; }
        .photo-preview { width:100px; height:100px; border-radius:50%; object-fit:cover; border:3px solid #FFD700; }
        .tab-selector .nav-link { color:#8B0000; font-weight:600; }
        .tab-selector .nav-link.active { background:#8B0000; color:#FFD700; }
        .badge-temple { background:#8B0000; color:#FFD700; padding:4px 10px; border-radius:15px; font-size:0.78em; }
        .family-member-card { background:#f8f9fa; border:1px solid #dee2e6; border-radius:10px; padding:12px; margin-bottom:8px; position:relative; }
        .yearly-pooja-entry { background:#FFF8DC; border:1px solid #FFD700; border-radius:8px; padding:8px; margin-bottom:6px; }

        /* Login */
        .login-container { min-height:100vh; display:flex; align-items:center; justify-content:center; position:relative; overflow:hidden; }
        .login-bg-img { position:absolute; top:0; left:0; width:100%; height:100%; background-size:cover; background-position:center; z-index:0; filter:brightness(0.35) saturate(1.2); }
        .login-overlay { position:absolute; top:0; left:0; width:100%; height:100%; background:linear-gradient(135deg,rgba(139,0,0,0.7),rgba(220,20,60,0.6),rgba(255,69,0,0.7)); z-index:1; }
        .login-card { background:rgba(255,255,255,0.96); border-radius:20px; padding:35px; width:420px; box-shadow:0 20px 60px rgba(0,0,0,0.4); position:relative; z-index:2; backdrop-filter:blur(10px); }
        .login-amman { width:100px; height:100px; border-radius:50%; border:4px solid #FFD700; object-fit:cover; box-shadow:0 0 30px rgba(255,215,0,0.6); display:block; margin:0 auto 12px; background:#FFF8DC; }

        /* Bill Print Header */
        .bill-hdr { display:flex; align-items:center; justify-content:center; margin-bottom:12px; padding-bottom:12px; border-bottom:3px double #8B0000; }
        .bill-hdr img { width:65px; height:65px; border-radius:50%; border:2px solid #FFD700; object-fit:cover; margin-right:18px; background:#FFF8DC; }
        .bill-hdr-info { text-align:center; flex:1; }
        .bill-hdr-info h3 { color:#8B0000; margin:0; font-size:1.15em; font-weight:700; }
        .bill-hdr-info h5 { color:#DC143C; margin:1px 0; font-size:0.88em; font-weight:600; }
        .bill-hdr-info p { margin:1px 0; color:#555; font-size:0.78em; }

        .deleted-row { text-decoration:line-through; opacity:0.5; background:#ffe0e0 !important; }

        @media(max-width:768px) { .sidebar{width:0;overflow:hidden;} .sidebar.show{width:270px;} .main-content{margin-left:0;} }
        @media print { .sidebar,.top-bar,.no-print{display:none!important;} .main-content{margin-left:0!important;padding:0!important;} .content-card{box-shadow:none!important;} }
    </style>
</head>
<body>
{% if current_user.is_authenticated %}
<div class="sidebar" id="sidebar">
    <div class="sidebar-header">
        <img src="{{ amman_image }}" alt="Amman" class="amman-round">
        <h4>{{ temple_name }}</h4>
        <div class="addr">{{ temple_trust }} - {{ temple_address_line3 }}</div>
        <small style="color:#FFD700;opacity:0.8;display:block;margin-top:6px;">
            <i class="fas fa-user"></i> {{ current_user.full_name or current_user.username }}
            {% if current_user.role=='admin' %}<span class="badge bg-warning text-dark" style="font-size:0.65em;">ADMIN</span>{% endif %}
        </small>
    </div>
    <div class="sidebar-menu">
        <a href="{{ url_for('dashboard') }}" class="{% if request.endpoint=='dashboard' %}active{% endif %}"><i class="fas fa-tachometer-alt"></i> Dashboard</a>
        <a href="{{ url_for('devotees') }}" class="{% if request.endpoint in ['devotees','add_devotee','edit_devotee','view_devotee'] %}active{% endif %}"><i class="fas fa-users"></i> Devotees</a>
        <a href="{{ url_for('billing') }}" class="{% if request.endpoint in ['billing','new_bill','view_bill'] %}active{% endif %}"><i class="fas fa-file-invoice"></i> Billing</a>
        <a href="{{ url_for('expenses_page') }}" class="{% if request.endpoint=='expenses_page' %}active{% endif %}"><i class="fas fa-money-bill-wave"></i> Expenses</a>
        <a href="{{ url_for('reports') }}" class="{% if request.endpoint=='reports' %}active{% endif %}"><i class="fas fa-chart-bar"></i> Reports</a>
        <div class="divider"></div>
        <a href="{{ url_for('samaya_vakuppu') }}" class="{% if request.endpoint in ['samaya_vakuppu','add_samaya','edit_samaya'] %}active{% endif %}"><i class="fas fa-graduation-cap"></i> Samaya Vakuppu</a>
        <a href="{{ url_for('thirumana_mandapam') }}" class="{% if request.endpoint in ['thirumana_mandapam','add_mandapam','edit_mandapam'] %}active{% endif %}"><i class="fas fa-building"></i> Thirumana Mandapam</a>
        <div class="divider"></div>
        <a href="{{ url_for('daily_pooja_page') }}" class="{% if request.endpoint=='daily_pooja_page' %}active{% endif %}"><i class="fas fa-om"></i> Daily Pooja</a>
        <a href="{{ url_for('settings') }}" class="{% if request.endpoint=='settings' %}active{% endif %}"><i class="fas fa-cog"></i> Settings</a>
        {% if current_user.role=='admin' %}
        <a href="{{ url_for('user_management') }}" class="{% if request.endpoint=='user_management' %}active{% endif %}"><i class="fas fa-user-shield"></i> User Management</a>
        <a href="{{ url_for('deleted_bills') }}" class="{% if request.endpoint=='deleted_bills' %}active{% endif %}"><i class="fas fa-trash-restore"></i> Deleted Bills</a>
        {% endif %}
        <div class="divider"></div>
        <a href="{{ url_for('upload_temple_images') }}" class="{% if request.endpoint=='upload_temple_images' %}active{% endif %}"><i class="fas fa-image"></i> Temple Images</a>
        <a href="{{ url_for('logout') }}"><i class="fas fa-sign-out-alt"></i> Logout</a>
    </div>
</div>
<div class="main-content">
    <div class="top-bar">
        <div>
            <button class="btn btn-sm btn-outline-danger d-md-none me-2" onclick="document.getElementById('sidebar').classList.toggle('show')"><i class="fas fa-bars"></i></button>
            <img src="{{ amman_image }}" alt="" class="amman-sm">
            <span style="color:#8B0000;font-weight:600;"><i class="fas fa-om"></i> {{ page_title|default('Dashboard') }}</span>
        </div>
        <div><span class="text-muted"><i class="fas fa-calendar"></i> {{ now().strftime('%d %B %Y, %A') }}</span></div>
    </div>
    {% with messages = get_flashed_messages(with_categories=true) %}{% if messages %}{% for cat, msg in messages %}
    <div class="alert alert-{{ cat }} alert-dismissible fade show">{{ msg }}<button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>
    {% endfor %}{% endif %}{% endwith %}
    {% block content %}{% endblock %}
</div>
{% else %}
{% block login_content %}{% endblock %}
{% endif %}
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
<script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
<script src="https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js"></script>
<script>$(document).ready(function(){if($.fn.DataTable){$('.data-table').DataTable({pageLength:10,responsive:true,order:[[0,'desc']]});}});</script>
{% block extra_js %}{% endblock %}
</body>
</html>
"""

LOGIN_TEMPLATE = """
{% extends "main" %}
{% block login_content %}
<div class="login-container">
    {% if temple_bg %}
    <div class="login-bg-img" style="background-image:url('{{ temple_bg }}');"></div>
    {% else %}
    <div class="login-bg-img" style="background:url('https://images.unsplash.com/photo-1604948501466-4e9c339b9c24?w=1920&q=80') center/cover no-repeat;"></div>
    {% endif %}
    <div class="login-overlay"></div>
    <div class="login-card">
        <div class="text-center mb-3">
            <img src="{{ amman_image }}" alt="Amman" class="login-amman">
            <h4 style="color:#8B0000;font-weight:700;margin-bottom:2px;">{{ temple_name }}</h4>
            <p style="color:#DC143C;font-size:0.82em;margin-bottom:1px;font-weight:600;">{{ temple_trust }} - {{ temple_address_line3 }}</p>
            <hr style="border-color:#FFD700;margin:10px 0;">
            <p class="text-muted" style="font-size:0.85em;">Please login to continue</p>
        </div>
        {% with messages = get_flashed_messages(with_categories=true) %}{% if messages %}{% for cat, msg in messages %}
        <div class="alert alert-{{ cat }} py-2">{{ msg }}</div>{% endfor %}{% endif %}{% endwith %}
        <form method="POST">
            <div class="mb-3">
                <label class="form-label">Username</label>
                <div class="input-group">
                    <span class="input-group-text" style="background:#8B0000;color:#FFD700;"><i class="fas fa-user"></i></span>
                    <input type="text" name="username" class="form-control" required placeholder="Enter username">
                </div>
            </div>
            <div class="mb-3">
                <label class="form-label">Password</label>
                <div class="input-group">
                    <span class="input-group-text" style="background:#8B0000;color:#FFD700;"><i class="fas fa-lock"></i></span>
                    <input type="password" name="password" class="form-control" required placeholder="Enter password">
                </div>
            </div>
            <button type="submit" class="btn btn-temple w-100 py-2"><i class="fas fa-sign-in-alt"></i> Login</button>
        </form>
        <div class="text-center mt-3"><small style="color:#aaa;">🕉️ Temple Management System</small></div>
    </div>
</div>
{% endblock %}
"""

DASHBOARD_TEMPLATE = """
{% extends "main" %}
{% block content %}
<div class="news-ticker-container">
    <div class="news-ticker">
        {% for msg in ticker_messages %}<span>🎂 {{ msg }}</span>{% endfor %}
        {% if not ticker_messages %}<span>🕉️ Welcome to {{ temple_name }} - {{ temple_trust }} 🙏</span>{% endif %}
    </div>
</div>
<div class="text-center mb-4">
    <button class="period-btn {% if period=='daily' %}active{% endif %}" onclick="location.href='?period=daily'">Daily</button>
    <button class="period-btn {% if period=='weekly' %}active{% endif %}" onclick="location.href='?period=weekly'">Weekly</button>
    <button class="period-btn {% if period=='monthly' %}active{% endif %}" onclick="location.href='?period=monthly'">Monthly</button>
    <button class="period-btn {% if period=='yearly' %}active{% endif %}" onclick="location.href='?period=yearly'">Yearly</button>
</div>
<div class="row mb-4">
    <div class="col-md-3 mb-3"><div class="stat-card income"><i class="fas fa-arrow-up si"></i><h6>{{ period|title }} Income</h6><h3>₹{{ '{:,.2f}'.format(total_income) }}</h3></div></div>
    <div class="col-md-3 mb-3"><div class="stat-card expense"><i class="fas fa-arrow-down si"></i><h6>{{ period|title }} Expenses</h6><h3>₹{{ '{:,.2f}'.format(total_expenses) }}</h3></div></div>
    <div class="col-md-3 mb-3"><div class="stat-card devotees"><i class="fas fa-users si"></i><h6>Total Devotees</h6><h3>{{ total_devotees }}</h3></div></div>
    <div class="col-md-3 mb-3"><div class="stat-card bills"><i class="fas fa-file-invoice si"></i><h6>{{ period|title }} Bills</h6><h3>{{ total_bills }}</h3></div></div>
</div>
<div class="row">
    <div class="col-md-6 mb-4">
        <div class="content-card">
            <h5><i class="fas fa-om"></i> Today's Pooja Schedule</h5>
            {% for p in daily_poojas %}
            <div class="pooja-card"><div class="d-flex justify-content-between align-items-center"><div><strong>{{ p.pooja_name }}</strong><br><small class="text-muted">{{ p.description or '' }}</small></div><span class="pooja-time">{{ p.pooja_time or 'TBD' }}</span></div></div>
            {% endfor %}
            {% if not daily_poojas %}<p class="text-muted text-center py-3">No pooja scheduled</p>{% endif %}
        </div>
    </div>
    <div class="col-md-6 mb-4">
        <div class="content-card">
            <h5><i class="fas fa-birthday-cake"></i> Today's Birthdays</h5>
            {% for d in birthdays %}
            <div class="d-flex align-items-center p-2 mb-2" style="background:#FFF8DC;border-radius:8px;">
                <div style="width:38px;height:38px;background:#DC143C;color:white;border-radius:50%;display:flex;align-items:center;justify-content:center;margin-right:10px;">🎂</div>
                <div><strong>{{ d.name }}</strong><br><small class="text-muted">{{ d.mobile_no or '' }}</small></div>
            </div>
            {% endfor %}
            {% if not birthdays %}<p class="text-muted text-center py-3">No birthdays today</p>{% endif %}
        </div>
    </div>
</div>
<div class="content-card">
    <h5><i class="fas fa-file-invoice"></i> Recent Bills</h5>
    <div class="table-responsive"><table class="table table-hover">
        <thead><tr><th>Bill No</th><th>Date</th><th>Name</th><th>Pooja</th><th>Amount</th></tr></thead>
        <tbody>{% for b in recent_bills %}<tr><td>{{ b.bill_number }}</td><td>{{ b.bill_date.strftime('%d/%m/%Y') }}</td><td>{{ b.devotee.name if b.devotee else b.guest_name }}</td><td>{{ b.pooja_type.name if b.pooja_type else '-' }}</td><td><strong>₹{{ '{:,.2f}'.format(b.amount) }}</strong></td></tr>{% endfor %}</tbody>
    </table></div>
</div>
{% endblock %}
"""

DEVOTEES_TEMPLATE = """
{% extends "main" %}
{% block content %}
<div class="content-card">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h5 class="mb-0"><i class="fas fa-users"></i> Enrolled Devotees</h5>
        <a href="{{ url_for('add_devotee') }}" class="btn btn-temple"><i class="fas fa-plus"></i> Add</a>
    </div>
    <div class="row mb-3"><div class="col-md-4"><input type="text" id="si" class="form-control" placeholder="Search..." onkeyup="ft()"></div></div>
    <div class="table-responsive"><table class="table table-hover" id="dt">
        <thead><tr><th>#</th><th>Photo</th><th>Name</th><th>Mobile</th><th>WhatsApp</th><th>Natchathiram</th><th>Family</th><th>Actions</th></tr></thead>
        <tbody>{% for d in devotees %}<tr>
            <td>{{ d.id }}</td>
            <td>{% if d.photo_filename %}<img src="{{ url_for('uploaded_file',folder='devotees',filename=d.photo_filename) }}" style="width:38px;height:38px;border-radius:50%;object-fit:cover;border:2px solid #FFD700;">{% else %}<div style="width:38px;height:38px;background:#8B0000;color:#FFD700;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:bold;">{{ d.name[0] }}</div>{% endif %}</td>
            <td><strong>{{ d.name }}</strong></td><td>{{ d.mobile_no or '-' }}</td><td>{{ d.whatsapp_no or '-' }}</td><td>{{ d.natchathiram or '-' }}</td>
            <td><span class="badge-temple">{{ d.family_members.count() }}</span></td>
            <td>
                <a href="{{ url_for('view_devotee',id=d.id) }}" class="btn btn-sm btn-info text-white"><i class="fas fa-eye"></i></a>
                <a href="{{ url_for('edit_devotee',id=d.id) }}" class="btn btn-sm btn-warning"><i class="fas fa-edit"></i></a>
                <form method="POST" action="{{ url_for('delete_devotee',id=d.id) }}" style="display:inline" onsubmit="return confirm('Delete?')"><button class="btn btn-sm btn-danger"><i class="fas fa-trash"></i></button></form>
            </td>
        </tr>{% endfor %}</tbody>
    </table></div>
</div>
{% endblock %}
{% block extra_js %}<script>function ft(){var v=document.getElementById("si").value.toLowerCase();document.querySelectorAll("#dt tbody tr").forEach(function(r){r.style.display=r.textContent.toLowerCase().includes(v)?"":"none";});}</script>{% endblock %}
"""

ADD_DEVOTEE_TEMPLATE = """
{% extends "main" %}
{% block content %}
<div class="content-card">
    <h5><i class="fas fa-user-plus"></i> {{ 'Edit' if devotee else 'Add New' }} Devotee</h5>
    <form method="POST" enctype="multipart/form-data">
        <div class="row">
            <div class="col-md-8"><div class="row">
                <div class="col-md-6 mb-3"><label class="form-label">Name *</label><input type="text" name="name" class="form-control" required value="{{ devotee.name if devotee else '' }}"></div>
                <div class="col-md-6 mb-3"><label class="form-label">DOB</label><input type="date" name="dob" class="form-control" value="{{ devotee.dob.strftime('%Y-%m-%d') if devotee and devotee.dob else '' }}"></div>
                <div class="col-md-6 mb-3"><label class="form-label">Relation</label><select name="relation_type" class="form-select"><option value="">--</option>{% for r in relation_types %}<option value="{{ r }}" {{ 'selected' if devotee and devotee.relation_type==r }}>{{ r }}</option>{% endfor %}</select></div>
                <div class="col-md-6 mb-3"><label class="form-label">Mobile</label><input type="text" name="mobile_no" class="form-control" value="{{ devotee.mobile_no if devotee else '' }}"></div>
                <div class="col-md-6 mb-3"><label class="form-label">WhatsApp</label><input type="text" name="whatsapp_no" class="form-control" value="{{ devotee.whatsapp_no if devotee else '' }}"></div>
                <div class="col-md-6 mb-3"><label class="form-label">Wedding Day</label><input type="date" name="wedding_day" class="form-control" value="{{ devotee.wedding_day.strftime('%Y-%m-%d') if devotee and devotee.wedding_day else '' }}"></div>
                <div class="col-md-6 mb-3"><label class="form-label">Natchathiram</label><select name="natchathiram" class="form-select"><option value="">--</option>{% for n in natchathiram_list %}<option value="{{ n }}" {{ 'selected' if devotee and devotee.natchathiram==n }}>{{ n }}</option>{% endfor %}</select></div>
                <div class="col-md-12 mb-3"><label class="form-label">Address</label><textarea name="address" class="form-control" rows="2">{{ devotee.address if devotee else '' }}</textarea></div>
            </div></div>
            <div class="col-md-4 text-center">
                <label class="form-label">Photo</label><div class="mb-2">
                {% if devotee and devotee.photo_filename %}<img src="{{ url_for('uploaded_file',folder='devotees',filename=devotee.photo_filename) }}" class="photo-preview" id="pp" style="width:140px;height:140px;">
                {% else %}<div id="pp" style="width:140px;height:140px;background:#f0f0f0;border-radius:50%;display:flex;align-items:center;justify-content:center;margin:auto;border:3px dashed #ccc;"><i class="fas fa-camera fa-2x text-muted"></i></div>{% endif %}
                </div><input type="file" name="photo" class="form-control" accept="image/*" onchange="ppv(this)">
            </div>
        </div>
        <div class="mt-4"><div class="d-flex justify-content-between align-items-center mb-3"><h6 style="color:#8B0000;font-weight:700;"><i class="fas fa-om"></i> Yearly Pooja</h6><button type="button" class="btn btn-sm btn-gold" onclick="ayp()"><i class="fas fa-plus"></i> Add</button></div>
        <div id="ypc">{% if devotee %}{% for yp in devotee.yearly_poojas.all() %}<div class="yearly-pooja-entry"><input type="hidden" name="yp_id[]" value="{{ yp.id }}"><div class="row"><div class="col-md-4 mb-2"><select name="yp_pooja_type[]" class="form-select form-select-sm"><option value="">--</option>{% for pt in pooja_types %}<option value="{{ pt.id }}" {{ 'selected' if yp.pooja_type_id==pt.id }}>{{ pt.name }}</option>{% endfor %}</select></div><div class="col-md-3 mb-2"><input type="date" name="yp_date[]" class="form-control form-control-sm" value="{{ yp.pooja_date.strftime('%Y-%m-%d') if yp.pooja_date else '' }}"></div><div class="col-md-4 mb-2"><input type="text" name="yp_notes[]" class="form-control form-control-sm" placeholder="Notes" value="{{ yp.notes or '' }}"></div><div class="col-md-1"><button type="button" class="btn btn-sm btn-danger" onclick="this.closest('.yearly-pooja-entry').remove()"><i class="fas fa-times"></i></button></div></div></div>{% endfor %}{% endif %}</div></div>
        <div class="mt-4"><div class="d-flex justify-content-between align-items-center mb-3"><h6 style="color:#8B0000;font-weight:700;"><i class="fas fa-users"></i> Family Members</h6><button type="button" class="btn btn-sm btn-gold" onclick="afm()"><i class="fas fa-plus"></i> Add</button></div>
        <div id="fmc">{% if devotee %}{% for fm in devotee.family_members.all() %}<div class="family-member-card"><input type="hidden" name="fm_id[]" value="{{ fm.id }}"><button type="button" class="btn btn-sm btn-danger position-absolute" style="top:5px;right:5px;" onclick="this.closest('.family-member-card').remove()"><i class="fas fa-times"></i></button><div class="row"><div class="col-md-3 mb-2"><label class="form-label">Name</label><input type="text" name="fm_name[]" class="form-control form-control-sm" value="{{ fm.name }}"></div><div class="col-md-2 mb-2"><label class="form-label">DOB</label><input type="date" name="fm_dob[]" class="form-control form-control-sm" value="{{ fm.dob.strftime('%Y-%m-%d') if fm.dob else '' }}"></div><div class="col-md-2 mb-2"><label class="form-label">Relation</label><select name="fm_relation[]" class="form-select form-select-sm"><option value="">--</option>{% for r in relation_types %}<option value="{{ r }}" {{ 'selected' if fm.relation_type==r }}>{{ r }}</option>{% endfor %}</select></div><div class="col-md-2 mb-2"><label class="form-label">Star</label><select name="fm_natchathiram[]" class="form-select form-select-sm"><option value="">--</option>{% for n in natchathiram_list %}<option value="{{ n }}" {{ 'selected' if fm.natchathiram==n }}>{{ n }}</option>{% endfor %}</select></div><div class="col-md-3 mb-2"><label class="form-label">Mobile</label><input type="text" name="fm_mobile[]" class="form-control form-control-sm" value="{{ fm.mobile_no or '' }}"></div></div></div>{% endfor %}{% endif %}</div></div>
        <div class="mt-4"><button type="submit" class="btn btn-temple"><i class="fas fa-save"></i> Save</button> <a href="{{ url_for('devotees') }}" class="btn btn-secondary ms-2">Cancel</a></div>
    </form>
</div>
{% endblock %}
{% block extra_js %}
<script>
function afm(){document.getElementById('fmc').insertAdjacentHTML('beforeend','<div class="family-member-card"><input type="hidden" name="fm_id[]" value="new"><button type="button" class="btn btn-sm btn-danger position-absolute" style="top:5px;right:5px;" onclick="this.closest(\\\'.family-member-card\\\').remove()"><i class="fas fa-times"></i></button><div class="row"><div class="col-md-3 mb-2"><label class="form-label">Name</label><input type="text" name="fm_name[]" class="form-control form-control-sm"></div><div class="col-md-2 mb-2"><label class="form-label">DOB</label><input type="date" name="fm_dob[]" class="form-control form-control-sm"></div><div class="col-md-2 mb-2"><label class="form-label">Relation</label><select name="fm_relation[]" class="form-select form-select-sm"><option value="">--</option>{% for r in relation_types %}<option value="{{ r }}">{{ r }}</option>{% endfor %}</select></div><div class="col-md-2 mb-2"><label class="form-label">Star</label><select name="fm_natchathiram[]" class="form-select form-select-sm"><option value="">--</option>{% for n in natchathiram_list %}<option value="{{ n }}">{{ n }}</option>{% endfor %}</select></div><div class="col-md-3 mb-2"><label class="form-label">Mobile</label><input type="text" name="fm_mobile[]" class="form-control form-control-sm"></div></div></div>');}
function ayp(){document.getElementById('ypc').insertAdjacentHTML('beforeend','<div class="yearly-pooja-entry"><input type="hidden" name="yp_id[]" value="new"><div class="row"><div class="col-md-4 mb-2"><select name="yp_pooja_type[]" class="form-select form-select-sm"><option value="">--</option>{% for pt in pooja_types %}<option value="{{ pt.id }}">{{ pt.name }}</option>{% endfor %}</select></div><div class="col-md-3 mb-2"><input type="date" name="yp_date[]" class="form-control form-control-sm"></div><div class="col-md-4 mb-2"><input type="text" name="yp_notes[]" class="form-control form-control-sm" placeholder="Notes"></div><div class="col-md-1"><button type="button" class="btn btn-sm btn-danger" onclick="this.closest(\\\'.yearly-pooja-entry\\\').remove()"><i class="fas fa-times"></i></button></div></div></div>');}
function ppv(i){if(i.files&&i.files[0]){var r=new FileReader();r.onload=function(e){var p=document.getElementById('pp');if(p.tagName==='IMG'){p.src=e.target.result;}else{p.outerHTML='<img src="'+e.target.result+'" class="photo-preview" id="pp" style="width:140px;height:140px;">';}};r.readAsDataURL(i.files[0]);}}
</script>
{% endblock %}
"""

VIEW_DEVOTEE_TEMPLATE = """
{% extends "main" %}
{% block content %}
<div class="content-card">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h5 class="mb-0"><i class="fas fa-user"></i> Devotee Details</h5>
        <div><a href="{{ url_for('edit_devotee',id=devotee.id) }}" class="btn btn-warning btn-sm"><i class="fas fa-edit"></i> Edit</a> <a href="{{ url_for('devotees') }}" class="btn btn-secondary btn-sm"><i class="fas fa-arrow-left"></i> Back</a></div>
    </div>
    <div class="row">
        <div class="col-md-3 text-center">
            {% if devotee.photo_filename %}<img src="{{ url_for('uploaded_file',folder='devotees',filename=devotee.photo_filename) }}" class="photo-preview" style="width:140px;height:140px;">{% else %}<div style="width:140px;height:140px;background:#8B0000;color:#FFD700;border-radius:50%;display:flex;align-items:center;justify-content:center;margin:auto;font-size:3em;font-weight:bold;">{{ devotee.name[0] }}</div>{% endif %}
            <h5 class="mt-3" style="color:#8B0000;">{{ devotee.name }}</h5><span class="badge-temple">ID: {{ devotee.id }}</span>
        </div>
        <div class="col-md-9"><div class="row">
            <div class="col-md-4 mb-3"><label class="form-label text-muted">DOB</label><p class="fw-bold">{{ devotee.dob.strftime('%d/%m/%Y') if devotee.dob else '-' }}</p></div>
            <div class="col-md-4 mb-3"><label class="form-label text-muted">Relation</label><p class="fw-bold">{{ devotee.relation_type or '-' }}</p></div>
            <div class="col-md-4 mb-3"><label class="form-label text-muted">Mobile</label><p class="fw-bold">{{ devotee.mobile_no or '-' }}</p></div>
            <div class="col-md-4 mb-3"><label class="form-label text-muted">WhatsApp</label><p class="fw-bold">{{ devotee.whatsapp_no or '-' }}</p></div>
            <div class="col-md-4 mb-3"><label class="form-label text-muted">Wedding</label><p class="fw-bold">{{ devotee.wedding_day.strftime('%d/%m/%Y') if devotee.wedding_day else '-' }}</p></div>
            <div class="col-md-4 mb-3"><label class="form-label text-muted">Natchathiram</label><p class="fw-bold">{{ devotee.natchathiram or '-' }}</p></div>
            <div class="col-md-12 mb-3"><label class="form-label text-muted">Address</label><p class="fw-bold">{{ devotee.address or '-' }}</p></div>
        </div></div>
    </div>
    <div class="mt-4"><h6 style="color:#8B0000;border-bottom:2px solid #FFD700;padding-bottom:8px;"><i class="fas fa-users"></i> Family ({{ devotee.family_members.count() }})</h6>
    {% for fm in devotee.family_members.all() %}<div class="family-member-card"><div class="row"><div class="col-md-3"><strong>{{ fm.name }}</strong></div><div class="col-md-2">{{ fm.relation_type or '-' }}</div><div class="col-md-2">{{ fm.dob.strftime('%d/%m/%Y') if fm.dob else '-' }}</div><div class="col-md-2">{{ fm.natchathiram or '-' }}</div><div class="col-md-3">{{ fm.mobile_no or '-' }}</div></div></div>{% endfor %}</div>
    <div class="mt-4"><h6 style="color:#8B0000;border-bottom:2px solid #FFD700;padding-bottom:8px;"><i class="fas fa-om"></i> Yearly Poojas ({{ devotee.yearly_poojas.count() }})</h6>
    {% for yp in devotee.yearly_poojas.all() %}<div class="yearly-pooja-entry"><div class="row"><div class="col-md-4"><strong>{{ yp.pooja_name or '-' }}</strong></div><div class="col-md-3">{{ yp.pooja_date.strftime('%d/%m/%Y') if yp.pooja_date else '-' }}</div><div class="col-md-5">{{ yp.notes or '-' }}</div></div></div>{% endfor %}</div>
    <div class="mt-4"><h6 style="color:#8B0000;border-bottom:2px solid #FFD700;padding-bottom:8px;"><i class="fas fa-file-invoice"></i> Bills</h6>
    <div class="table-responsive"><table class="table table-sm"><thead><tr><th>Bill</th><th>Date</th><th>Pooja</th><th>Amount</th></tr></thead><tbody>{% for b in devotee.bills %}{% if not b.is_deleted %}<tr><td>{{ b.bill_number }}</td><td>{{ b.bill_date.strftime('%d/%m/%Y') }}</td><td>{{ b.pooja_type.name if b.pooja_type else '-' }}</td><td>₹{{ '{:,.2f}'.format(b.amount) }}</td></tr>{% endif %}{% endfor %}</tbody></table></div></div>
</div>
{% endblock %}
"""

BILLING_TEMPLATE = """
{% extends "main" %}
{% block content %}
<div class="content-card">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h5 class="mb-0"><i class="fas fa-file-invoice"></i> Bills</h5>
        <a href="{{ url_for('new_bill') }}" class="btn btn-temple"><i class="fas fa-plus"></i> New Bill</a>
    </div>
    <form method="GET" class="row mb-3">
        <div class="col-md-3"><label class="form-label">From</label><input type="date" name="from_date" class="form-control" value="{{ from_date }}"></div>
        <div class="col-md-3"><label class="form-label">To</label><input type="date" name="to_date" class="form-control" value="{{ to_date }}"></div>
        <div class="col-md-3 d-flex align-items-end"><button type="submit" class="btn btn-temple me-2"><i class="fas fa-filter"></i> Filter</button><a href="{{ url_for('billing') }}" class="btn btn-secondary">Reset</a></div>
    </form>
    <div class="table-responsive"><table class="table table-hover data-table">
        <thead><tr><th>Bill No</th><th>Manual</th><th>Date</th><th>Type</th><th>Name</th><th>Pooja</th><th>Amount</th><th>Actions</th></tr></thead>
        <tbody>{% for b in bills %}<tr class="{% if b.is_deleted %}deleted-row{% endif %}">
            <td>{{ b.bill_number }}</td><td>{{ b.manual_bill_no or '-' }}</td><td>{{ b.bill_date.strftime('%d/%m/%Y') }}</td>
            <td>{% if b.devotee_type=='enrolled' %}<span class="badge bg-success">Enrolled</span>{% else %}<span class="badge bg-info">Guest</span>{% endif %}</td>
            <td>{{ b.devotee.name if b.devotee else b.guest_name }}</td><td>{{ b.pooja_type.name if b.pooja_type else '-' }}</td>
            <td><strong>₹{{ '{:,.2f}'.format(b.amount) }}</strong></td>
            <td>{% if not b.is_deleted %}
                <a href="{{ url_for('view_bill',id=b.id) }}" class="btn btn-sm btn-info text-white" title="View"><i class="fas fa-eye"></i></a>
                <a href="{{ url_for('bill_pdf',id=b.id) }}" class="btn btn-sm btn-success text-white" title="PDF"><i class="fas fa-file-pdf"></i></a>
                {% if current_user.role=='admin' %}
                <button class="btn btn-sm btn-danger" data-bs-toggle="modal" data-bs-target="#delM{{ b.id }}" title="Delete"><i class="fas fa-trash"></i></button>
                <div class="modal fade" id="delM{{ b.id }}" tabindex="-1"><div class="modal-dialog"><div class="modal-content">
                    <div class="modal-header" style="background:#DC143C;color:white;"><h5 class="modal-title"><i class="fas fa-exclamation-triangle"></i> Delete {{ b.bill_number }}</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div>
                    <form method="POST" action="{{ url_for('delete_bill',id=b.id) }}"><div class="modal-body">
                        <p>Delete bill <strong>{{ b.bill_number }}</strong> (₹{{ '{:,.2f}'.format(b.amount) }})?</p>
                        <div class="mb-3"><label class="form-label">Reason *</label><textarea name="delete_reason" class="form-control" rows="3" required placeholder="Enter reason for deletion..."></textarea></div>
                    </div><div class="modal-footer"><button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button><button type="submit" class="btn btn-danger"><i class="fas fa-trash"></i> Delete</button></div></form>
                </div></div></div>
                {% endif %}
            {% else %}<span class="badge bg-danger">Deleted</span>{% endif %}</td>
        </tr>{% endfor %}</tbody>
    </table></div>
</div>
{% endblock %}
"""

NEW_BILL_TEMPLATE = """
{% extends "main" %}
{% block content %}
<div class="content-card">
    <h5><i class="fas fa-file-invoice"></i> New Bill</h5>
    <form method="POST">
        <div class="row">
            <div class="col-md-3 mb-3"><label class="form-label">Bill Number</label><input type="text" name="bill_number" class="form-control" value="{{ next_bill_no }}" readonly></div>
            <div class="col-md-3 mb-3"><label class="form-label">Manual Bill No</label><input type="text" name="manual_bill_no" class="form-control"></div>
            <div class="col-md-3 mb-3"><label class="form-label">Bill Book No</label><input type="text" name="bill_book_no" class="form-control"></div>
            <div class="col-md-3 mb-3"><label class="form-label">Date</label><input type="datetime-local" name="bill_date" class="form-control" value="{{ now().strftime('%Y-%m-%dT%H:%M') }}"></div>
        </div>
        <ul class="nav nav-tabs tab-selector mb-3"><li class="nav-item"><a class="nav-link active" data-bs-toggle="tab" href="#enrolled" onclick="document.getElementById('dt').value='enrolled'">Enrolled</a></li><li class="nav-item"><a class="nav-link" data-bs-toggle="tab" href="#guest" onclick="document.getElementById('dt').value='guest'">Guest</a></li></ul>
        <input type="hidden" name="devotee_type" id="dt" value="enrolled">
        <div class="tab-content">
            <div class="tab-pane fade show active" id="enrolled"><div class="row">
                <div class="col-md-6 mb-3"><label class="form-label">Select Devotee *</label><select name="devotee_id" id="ds" class="form-select" onchange="ldi()"><option value="">--</option>{% for d in devotees_list %}<option value="{{ d.id }}" data-mobile="{{ d.mobile_no or '' }}" data-address="{{ d.address or '' }}">{{ d.name }} (ID:{{ d.id }})</option>{% endfor %}</select></div>
                <div class="col-md-6 mb-3"><label class="form-label">Info</label><div id="di" class="form-control" style="background:#f8f9fa;min-height:38px;"></div></div>
            </div></div>
            <div class="tab-pane fade" id="guest"><div class="row">
                <div class="col-md-4 mb-3"><label class="form-label">Name *</label><input type="text" name="guest_name" class="form-control"></div>
                <div class="col-md-4 mb-3"><label class="form-label">Mobile</label><input type="text" name="guest_mobile" class="form-control"></div>
                <div class="col-md-4 mb-3"><label class="form-label">WhatsApp</label><input type="text" name="guest_whatsapp" class="form-control"></div>
                <div class="col-md-12 mb-3"><label class="form-label">Address</label><textarea name="guest_address" class="form-control" rows="2"></textarea></div>
            </div></div>
        </div>
        <div class="row">
            <div class="col-md-4 mb-3"><label class="form-label">Pooja *</label><select name="pooja_type_id" class="form-select" id="ps" onchange="ua()" required><option value="">--</option>{% for pt in pooja_types %}<option value="{{ pt.id }}" data-amount="{{ pt.amount }}">{{ pt.name }} (₹{{ pt.amount }})</option>{% endfor %}</select></div>
            <div class="col-md-4 mb-3"><label class="form-label">Amount *</label><input type="number" name="amount" id="af" class="form-control" step="0.01" required></div>
            <div class="col-md-4 mb-3"><label class="form-label">Notes</label><input type="text" name="notes" class="form-control"></div>
        </div>
        <button type="submit" class="btn btn-temple"><i class="fas fa-save"></i> Create Bill</button> <a href="{{ url_for('billing') }}" class="btn btn-secondary ms-2">Cancel</a>
    </form>
</div>
{% endblock %}
{% block extra_js %}<script>
function ldi(){var s=document.getElementById('ds'),o=s.options[s.selectedIndex];if(o.value){document.getElementById('di').innerHTML='<small><b>Mobile:</b> '+o.dataset.mobile+' | <b>Address:</b> '+o.dataset.address+'</small>';}else{document.getElementById('di').innerHTML='';}}
function ua(){var s=document.getElementById('ps'),o=s.options[s.selectedIndex];if(o.value){document.getElementById('af').value=o.dataset.amount;}}
</script>{% endblock %}
"""

VIEW_BILL_TEMPLATE = """
{% extends "main" %}
{% block content %}
<div class="content-card" id="bp">
    <div class="bill-hdr">
        <img src="{{ amman_image }}" alt="Amman">
        <div class="bill-hdr-info">
            <h3>🕉️ {{ temple_name }}</h3>
            <h5>{{ temple_trust }} - {{ temple_address_line3 }}</h5>
            <p>📞 Temple Office | Bill Receipt</p>
        </div>
        <img src="{{ amman_image }}" alt="Amman">
    </div>
    <div class="row mb-3">
        <div class="col-md-6"><table class="table table-borderless table-sm">
            <tr><td><strong>Bill No:</strong></td><td>{{ bill.bill_number }}</td></tr>
            <tr><td><strong>Manual Bill:</strong></td><td>{{ bill.manual_bill_no or '-' }}</td></tr>
            <tr><td><strong>Bill Book:</strong></td><td>{{ bill.bill_book_no or '-' }}</td></tr>
            <tr><td><strong>Date:</strong></td><td>{{ bill.bill_date.strftime('%d/%m/%Y %I:%M %p') }}</td></tr>
        </table></div>
        <div class="col-md-6"><table class="table table-borderless table-sm">
            {% if bill.devotee_type=='enrolled' and bill.devotee %}
            <tr><td><strong>Devotee:</strong></td><td>{{ bill.devotee.name }} (ID:{{ bill.devotee.id }})</td></tr>
            <tr><td><strong>Mobile:</strong></td><td>{{ bill.devotee.mobile_no or '-' }}</td></tr>
            <tr><td><strong>Address:</strong></td><td>{{ bill.devotee.address or '-' }}</td></tr>
            {% else %}
            <tr><td><strong>Guest:</strong></td><td>{{ bill.guest_name }}</td></tr>
            <tr><td><strong>Mobile:</strong></td><td>{{ bill.guest_mobile or '-' }}</td></tr>
            <tr><td><strong>Address:</strong></td><td>{{ bill.guest_address or '-' }}</td></tr>
            {% endif %}
        </table></div>
    </div>
    <table class="table table-bordered"><thead><tr><th>Pooja Type</th><th>Notes</th><th class="text-end">Amount</th></tr></thead>
    <tbody><tr><td>{{ bill.pooja_type.name if bill.pooja_type else '-' }}</td><td>{{ bill.notes or '-' }}</td><td class="text-end"><strong>₹{{ '{:,.2f}'.format(bill.amount) }}</strong></td></tr></tbody>
    <tfoot><tr><td colspan="2" class="text-end"><strong>Total:</strong></td><td class="text-end"><strong style="color:#8B0000;font-size:1.2em;">₹{{ '{:,.2f}'.format(bill.amount) }}</strong></td></tr></tfoot></table>
    <div class="text-center mt-3" style="border-top:1px dashed #ccc;padding-top:10px;"><small style="color:#888;">{{ temple_full_address }}</small></div>
    <div class="text-center mt-4 no-print">
        <button class="btn btn-temple" onclick="window.print()"><i class="fas fa-print"></i> Print</button>
        <a href="{{ url_for('bill_pdf',id=bill.id) }}" class="btn btn-success"><i class="fas fa-file-pdf"></i> PDF</a>
        <a href="{{ url_for('billing') }}" class="btn btn-secondary ms-2"><i class="fas fa-arrow-left"></i> Back</a>
    </div>
</div>
{% endblock %}
"""

BILL_PDF_TEMPLATE = """
<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
body{font-family:Arial,sans-serif;margin:20px;font-size:12px;}
.hdr{display:flex;align-items:center;justify-content:center;margin-bottom:10px;padding-bottom:10px;border-bottom:3px double #8B0000;}
.hdr img{width:60px;height:60px;border-radius:50%;border:2px solid #FFD700;margin:0 15px;}
.hdr-info{text-align:center;flex:1;}
.hdr-info h2{color:#8B0000;margin:0;font-size:16px;}
.hdr-info h4{color:#DC143C;margin:2px 0;font-size:12px;}
.hdr-info p{margin:1px 0;color:#555;font-size:10px;}
table{width:100%;border-collapse:collapse;margin:8px 0;}
table.info td{padding:3px 8px;font-size:11px;}
table.bill{border:1px solid #333;}
table.bill th{background:#8B0000;color:white;padding:6px;text-align:left;font-size:11px;}
table.bill td{border:1px solid #ccc;padding:5px;font-size:11px;}
.total{text-align:right;font-size:14px;font-weight:bold;color:#8B0000;margin-top:8px;}
.footer{text-align:center;margin-top:15px;padding-top:8px;border-top:1px dashed #ccc;font-size:9px;color:#888;}
</style></head><body>
<div class="hdr">
    <img src="{{ amman_image }}" alt="Amman">
    <div class="hdr-info">
        <h2>🕉️ {{ temple_name }}</h2>
        <h4>{{ temple_trust }}</h4>
        <p>{{ temple_address_line3 }}</p>
        <p>BILL RECEIPT</p>
    </div>
    <img src="{{ amman_image }}" alt="Amman">
</div>
<table class="info"><tr>
    <td><strong>Bill No:</strong> {{ bill.bill_number }}</td>
    <td><strong>Manual Bill:</strong> {{ bill.manual_bill_no or '-' }}</td>
    <td><strong>Date:</strong> {{ bill.bill_date.strftime('%d/%m/%Y %I:%M %p') }}</td>
</tr></table>
<table class="info"><tr>
    {% if bill.devotee_type=='enrolled' and bill.devotee %}
    <td><strong>Devotee:</strong> {{ bill.devotee.name }} (ID:{{ bill.devotee.id }})</td>
    <td><strong>Mobile:</strong> {{ bill.devotee.mobile_no or '-' }}</td>
    <td><strong>Address:</strong> {{ bill.devotee.address or '-' }}</td>
    {% else %}
    <td><strong>Guest:</strong> {{ bill.guest_name }}</td>
    <td><strong>Mobile:</strong> {{ bill.guest_mobile or '-' }}</td>
    <td><strong>Address:</strong> {{ bill.guest_address or '-' }}</td>
    {% endif %}
</tr></table>
<table class="bill"><thead><tr><th>Pooja Type</th><th>Notes</th><th style="text-align:right;">Amount</th></tr></thead>
<tbody><tr><td>{{ bill.pooja_type.name if bill.pooja_type else '-' }}</td><td>{{ bill.notes or '-' }}</td><td style="text-align:right;">₹{{ '{:,.2f}'.format(bill.amount) }}</td></tr></tbody></table>
<div class="total">Total: ₹{{ '{:,.2f}'.format(bill.amount) }}</div>
<div class="footer">{{ temple_full_address }}<br>🕉️ Thank you for your contribution 🙏</div>
</body></html>
"""

EXPENSES_TEMPLATE = """
{% extends "main" %}
{% block content %}
<div class="content-card">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h5 class="mb-0"><i class="fas fa-money-bill-wave"></i> Expenses</h5>
        <button class="btn btn-temple" data-bs-toggle="modal" data-bs-target="#aeM"><i class="fas fa-plus"></i> Add</button>
    </div>
    <form method="GET" class="row mb-3">
        <div class="col-md-3"><input type="date" name="from_date" class="form-control" value="{{ from_date }}"></div>
        <div class="col-md-3"><input type="date" name="to_date" class="form-control" value="{{ to_date }}"></div>
        <div class="col-md-3"><button type="submit" class="btn btn-temple"><i class="fas fa-filter"></i> Filter</button></div>
    </form>
    <div class="table-responsive"><table class="table table-hover data-table">
        <thead><tr><th>#</th><th>Date</th><th>Type</th><th>Description</th><th>Amount</th><th>Act</th></tr></thead>
        <tbody>{% for e in expenses %}<tr><td>{{ e.id }}</td><td>{{ e.expense_date.strftime('%d/%m/%Y') if e.expense_date else '-' }}</td><td>{{ e.expense_type.name if e.expense_type else '-' }}</td><td>{{ e.description or '-' }}</td><td><strong>₹{{ '{:,.2f}'.format(e.amount) }}</strong></td><td><form method="POST" action="{{ url_for('delete_expense',id=e.id) }}" style="display:inline" onsubmit="return confirm('Delete?')"><button class="btn btn-sm btn-danger"><i class="fas fa-trash"></i></button></form></td></tr>{% endfor %}</tbody>
    </table></div>
    <div class="text-end mt-3"><strong style="color:#8B0000;font-size:1.1em;">Total: ₹{{ '{:,.2f}'.format(expenses|sum(attribute='amount')) }}</strong></div>
</div>
<div class="modal fade" id="aeM" tabindex="-1"><div class="modal-dialog"><div class="modal-content">
    <div class="modal-header" style="background:#8B0000;color:#FFD700;"><h5 class="modal-title">Add Expense</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div>
    <form method="POST" action="{{ url_for('add_expense') }}"><div class="modal-body">
        <div class="mb-3"><label class="form-label">Type *</label><select name="expense_type_id" class="form-select" required><option value="">--</option>{% for et in expense_types %}<option value="{{ et.id }}">{{ et.name }}</option>{% endfor %}</select></div>
        <div class="mb-3"><label class="form-label">Amount *</label><input type="number" name="amount" class="form-control" step="0.01" required></div>
        <div class="mb-3"><label class="form-label">Date</label><input type="date" name="expense_date" class="form-control" value="{{ today }}"></div>
        <div class="mb-3"><label class="form-label">Description</label><textarea name="description" class="form-control" rows="2"></textarea></div>
    </div><div class="modal-footer"><button type="submit" class="btn btn-temple">Save</button></div></form>
</div></div></div>
{% endblock %}
"""

REPORTS_TEMPLATE = """
{% extends "main" %}
{% block content %}
<div class="content-card">
    <h5><i class="fas fa-chart-bar"></i> Reports</h5>
    <form method="GET" class="row mb-4">
        <div class="col-md-3"><label class="form-label">From</label><input type="date" name="from_date" class="form-control" value="{{ from_date }}"></div>
        <div class="col-md-3"><label class="form-label">To</label><input type="date" name="to_date" class="form-control" value="{{ to_date }}"></div>
        <div class="col-md-3 d-flex align-items-end"><button type="submit" class="btn btn-temple"><i class="fas fa-filter"></i> Generate</button></div>
    </form>
    <div class="row mb-4">
        <div class="col-md-4"><div class="stat-card income"><h6>Total Income</h6><h3>₹{{ '{:,.2f}'.format(total_income) }}</h3></div></div>
        <div class="col-md-4"><div class="stat-card expense"><h6>Total Expenses</h6><h3>₹{{ '{:,.2f}'.format(total_expenses) }}</h3></div></div>
        <div class="col-md-4"><div class="stat-card" style="background:linear-gradient(135deg,#4B0082,#8A2BE2);"><h6>Net Balance</h6><h3>₹{{ '{:,.2f}'.format(total_income-total_expenses) }}</h3></div></div>
    </div>
    <div class="row">
        <div class="col-md-6"><div class="content-card"><h6 style="color:#8B0000;"><i class="fas fa-chart-pie"></i> Income by Pooja</h6><table class="table table-sm"><thead><tr><th>Pooja</th><th>Count</th><th>Amount</th></tr></thead><tbody>{% for i in income_by_pooja %}<tr><td>{{ i.name }}</td><td>{{ i.count }}</td><td>₹{{ '{:,.2f}'.format(i.total) }}</td></tr>{% endfor %}</tbody></table></div></div>
        <div class="col-md-6"><div class="content-card"><h6 style="color:#8B0000;"><i class="fas fa-chart-pie"></i> Expenses by Type</h6><table class="table table-sm"><thead><tr><th>Type</th><th>Count</th><th>Amount</th></tr></thead><tbody>{% for i in expenses_by_type %}<tr><td>{{ i.name }}</td><td>{{ i.count }}</td><td>₹{{ '{:,.2f}'.format(i.total) }}</td></tr>{% endfor %}</tbody></table></div></div>
    </div>
    <div class="text-center mt-3 no-print"><button class="btn btn-temple" onclick="window.print()"><i class="fas fa-print"></i> Print</button></div>
</div>
{% endblock %}
"""

SAMAYA_TEMPLATE = """
{% extends "main" %}
{% block content %}
<div class="content-card">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h5 class="mb-0"><i class="fas fa-graduation-cap"></i> Samaya Vakuppu</h5>
        <a href="{{ url_for('add_samaya') }}" class="btn btn-temple"><i class="fas fa-plus"></i> Add</a>
    </div>
    <div class="table-responsive"><table class="table table-hover data-table">
        <thead><tr><th>#</th><th>Photo</th><th>Name</th><th>DOB</th><th>Father/Mother</th><th>Bond No</th><th>Date</th><th>Act</th></tr></thead>
        <tbody>{% for s in students %}<tr><td>{{ s.id }}</td><td>{% if s.photo_filename %}<img src="{{ url_for('uploaded_file',folder='samaya',filename=s.photo_filename) }}" style="width:38px;height:38px;border-radius:50%;object-fit:cover;">{% else %}<div style="width:38px;height:38px;background:#4169E1;color:white;border-radius:50%;display:flex;align-items:center;justify-content:center;">{{ s.student_name[0] }}</div>{% endif %}</td><td>{{ s.student_name }}</td><td>{{ s.dob.strftime('%d/%m/%Y') if s.dob else '-' }}</td><td>{{ s.father_mother_name or '-' }}</td><td>{{ s.bond_no or '-' }}</td><td>{{ s.bond_issue_date.strftime('%d/%m/%Y') if s.bond_issue_date else '-' }}</td><td><a href="{{ url_for('edit_samaya',id=s.id) }}" class="btn btn-sm btn-warning"><i class="fas fa-edit"></i></a> <form method="POST" action="{{ url_for('delete_samaya',id=s.id) }}" style="display:inline" onsubmit="return confirm('Delete?')"><button class="btn btn-sm btn-danger"><i class="fas fa-trash"></i></button></form></td></tr>{% endfor %}</tbody>
    </table></div>
</div>
{% endblock %}
"""

ADD_SAMAYA_TEMPLATE = """
{% extends "main" %}
{% block content %}
<div class="content-card">
    <h5><i class="fas fa-graduation-cap"></i> {{ 'Edit' if student else 'Add' }} Student</h5>
    <form method="POST" enctype="multipart/form-data"><div class="row">
        <div class="col-md-6 mb-3"><label class="form-label">Name *</label><input type="text" name="student_name" class="form-control" required value="{{ student.student_name if student else '' }}"></div>
        <div class="col-md-6 mb-3"><label class="form-label">DOB</label><input type="date" name="dob" class="form-control" value="{{ student.dob.strftime('%Y-%m-%d') if student and student.dob else '' }}"></div>
        <div class="col-md-6 mb-3"><label class="form-label">Father/Mother</label><input type="text" name="father_mother_name" class="form-control" value="{{ student.father_mother_name if student else '' }}"></div>
        <div class="col-md-6 mb-3"><label class="form-label">Bond No</label><input type="text" name="bond_no" class="form-control" value="{{ student.bond_no if student else '' }}"></div>
        <div class="col-md-6 mb-3"><label class="form-label">Bond Date</label><input type="date" name="bond_issue_date" class="form-control" value="{{ student.bond_issue_date.strftime('%Y-%m-%d') if student and student.bond_issue_date else '' }}"></div>
        <div class="col-md-6 mb-3"><label class="form-label">Bank</label><input type="text" name="bond_issuing_bank" class="form-control" value="{{ student.bond_issuing_bank if student else '' }}"></div>
        <div class="col-md-6 mb-3"><label class="form-label">Branch</label><input type="text" name="branch_of_bank" class="form-control" value="{{ student.branch_of_bank if student else '' }}"></div>
        <div class="col-md-12 mb-3"><label class="form-label">Address</label><textarea name="address" class="form-control" rows="2">{{ student.address if student else '' }}</textarea></div>
        <div class="col-md-6 mb-3"><label class="form-label">Photo</label><input type="file" name="photo" class="form-control" accept="image/*"></div>
        <div class="col-md-6 mb-3"><label class="form-label">Bond Scan</label><input type="file" name="bond_scan" class="form-control" accept="image/*,.pdf"></div>
    </div><button type="submit" class="btn btn-temple"><i class="fas fa-save"></i> Save</button> <a href="{{ url_for('samaya_vakuppu') }}" class="btn btn-secondary ms-2">Cancel</a></form>
</div>
{% endblock %}
"""

MANDAPAM_TEMPLATE = """
{% extends "main" %}
{% block content %}
<div class="content-card">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h5 class="mb-0"><i class="fas fa-building"></i> Thirumana Mandapam</h5>
        <a href="{{ url_for('add_mandapam') }}" class="btn btn-temple"><i class="fas fa-plus"></i> Add</a>
    </div>
    <div class="table-responsive"><table class="table table-hover data-table">
        <thead><tr><th>#</th><th>Name</th><th>Bond No</th><th>Date</th><th>Amount</th><th>Bonds</th><th>Act</th></tr></thead>
        <tbody>{% for m in records %}<tr><td>{{ m.id }}</td><td>{{ m.name }}</td><td>{{ m.bond_no or '-' }}</td><td>{{ m.bond_issued_date.strftime('%d/%m/%Y') if m.bond_issued_date else '-' }}</td><td>₹{{ '{:,.2f}'.format(m.amount) }}</td><td>{{ m.no_of_bond }}</td><td><a href="{{ url_for('edit_mandapam',id=m.id) }}" class="btn btn-sm btn-warning"><i class="fas fa-edit"></i></a> <form method="POST" action="{{ url_for('delete_mandapam',id=m.id) }}" style="display:inline" onsubmit="return confirm('Delete?')"><button class="btn btn-sm btn-danger"><i class="fas fa-trash"></i></button></form></td></tr>{% endfor %}</tbody>
    </table></div>
</div>
{% endblock %}
"""

ADD_MANDAPAM_TEMPLATE = """
{% extends "main" %}
{% block content %}
<div class="content-card">
    <h5><i class="fas fa-building"></i> {{ 'Edit' if record else 'Add' }} Record</h5>
    <form method="POST" enctype="multipart/form-data"><div class="row">
        <div class="col-md-6 mb-3"><label class="form-label">Name *</label><input type="text" name="name" class="form-control" required value="{{ record.name if record else '' }}"></div>
        <div class="col-md-6 mb-3"><label class="form-label">Bond No</label><input type="text" name="bond_no" class="form-control" value="{{ record.bond_no if record else '' }}"></div>
        <div class="col-md-6 mb-3"><label class="form-label">Bond Date</label><input type="date" name="bond_issued_date" class="form-control" value="{{ record.bond_issued_date.strftime('%Y-%m-%d') if record and record.bond_issued_date else '' }}"></div>
        <div class="col-md-3 mb-3"><label class="form-label">Amount</label><input type="number" name="amount" class="form-control" step="0.01" value="{{ record.amount if record else '0' }}"></div>
        <div class="col-md-3 mb-3"><label class="form-label">No of Bonds</label><input type="number" name="no_of_bond" class="form-control" value="{{ record.no_of_bond if record else '1' }}"></div>
        <div class="col-md-12 mb-3"><label class="form-label">Address</label><textarea name="address" class="form-control" rows="2">{{ record.address if record else '' }}</textarea></div>
        <div class="col-md-6 mb-3"><label class="form-label">Photo</label><input type="file" name="photo" class="form-control" accept="image/*"></div>
        <div class="col-md-6 mb-3"><label class="form-label">Bond Scan</label><input type="file" name="bond_scan" class="form-control" accept="image/*,.pdf"></div>
    </div><button type="submit" class="btn btn-temple"><i class="fas fa-save"></i> Save</button> <a href="{{ url_for('thirumana_mandapam') }}" class="btn btn-secondary ms-2">Cancel</a></form>
</div>
{% endblock %}
"""

DAILY_POOJA_TEMPLATE = """
{% extends "main" %}
{% block content %}
<div class="content-card">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h5 class="mb-0"><i class="fas fa-om"></i> Daily Pooja</h5>
        <button class="btn btn-temple" data-bs-toggle="modal" data-bs-target="#apM"><i class="fas fa-plus"></i> Add</button>
    </div>
    {% for p in poojas %}<div class="pooja-card"><div class="d-flex justify-content-between align-items-center"><div><strong style="font-size:1.05em;">{{ p.pooja_name }}</strong><br><small class="text-muted">{{ p.description or '' }}</small></div><div class="d-flex align-items-center"><span class="pooja-time me-3">{{ p.pooja_time or 'TBD' }}</span><form method="POST" action="{{ url_for('delete_daily_pooja',id=p.id) }}" style="display:inline"><button class="btn btn-sm btn-outline-danger"><i class="fas fa-trash"></i></button></form></div></div></div>{% endfor %}
</div>
<div class="modal fade" id="apM" tabindex="-1"><div class="modal-dialog"><div class="modal-content">
    <div class="modal-header" style="background:#8B0000;color:#FFD700;"><h5 class="modal-title">Add Daily Pooja</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div>
    <form method="POST" action="{{ url_for('add_daily_pooja') }}"><div class="modal-body">
        <div class="mb-3"><label class="form-label">Name *</label><input type="text" name="pooja_name" class="form-control" required></div>
        <div class="mb-3"><label class="form-label">Time</label><input type="text" name="pooja_time" class="form-control" placeholder="e.g. 6:00 AM"></div>
        <div class="mb-3"><label class="form-label">Description</label><textarea name="description" class="form-control" rows="2"></textarea></div>
    </div><div class="modal-footer"><button type="submit" class="btn btn-temple">Save</button></div></form>
</div></div></div>
{% endblock %}
"""

SETTINGS_TEMPLATE = """
{% extends "main" %}
{% block content %}
<div class="row">
    <div class="col-md-6 mb-4"><div class="content-card">
        <div class="d-flex justify-content-between align-items-center mb-3"><h5 class="mb-0"><i class="fas fa-om"></i> Pooja Types</h5><button class="btn btn-sm btn-temple" data-bs-toggle="modal" data-bs-target="#ptM"><i class="fas fa-plus"></i></button></div>
        <table class="table table-sm"><thead><tr><th>Name</th><th>Amount</th><th>Act</th></tr></thead><tbody>{% for pt in pooja_types %}<tr><td>{{ pt.name }}</td><td>₹{{ pt.amount }}</td><td><form method="POST" action="{{ url_for('delete_pooja_type',id=pt.id) }}" style="display:inline"><button class="btn btn-sm btn-danger"><i class="fas fa-trash"></i></button></form></td></tr>{% endfor %}</tbody></table>
    </div></div>
    <div class="col-md-6 mb-4"><div class="content-card">
        <div class="d-flex justify-content-between align-items-center mb-3"><h5 class="mb-0"><i class="fas fa-tags"></i> Expense Types</h5><button class="btn btn-sm btn-temple" data-bs-toggle="modal" data-bs-target="#etM"><i class="fas fa-plus"></i></button></div>
        <table class="table table-sm"><thead><tr><th>Name</th><th>Act</th></tr></thead><tbody>{% for et in expense_types %}<tr><td>{{ et.name }}</td><td><form method="POST" action="{{ url_for('delete_expense_type',id=et.id) }}" style="display:inline"><button class="btn btn-sm btn-danger"><i class="fas fa-trash"></i></button></form></td></tr>{% endfor %}</tbody></table>
    </div></div>
</div>
<div class="modal fade" id="ptM" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header" style="background:#8B0000;color:#FFD700;"><h5>Add Pooja Type</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><form method="POST" action="{{ url_for('add_pooja_type') }}"><div class="modal-body"><div class="mb-3"><label class="form-label">Name *</label><input type="text" name="name" class="form-control" required></div><div class="mb-3"><label class="form-label">Amount</label><input type="number" name="amount" class="form-control" step="0.01" value="0"></div></div><div class="modal-footer"><button type="submit" class="btn btn-temple">Save</button></div></form></div></div></div>
<div class="modal fade" id="etM" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header" style="background:#8B0000;color:#FFD700;"><h5>Add Expense Type</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><form method="POST" action="{{ url_for('add_expense_type') }}"><div class="modal-body"><div class="mb-3"><label class="form-label">Name *</label><input type="text" name="name" class="form-control" required></div></div><div class="modal-footer"><button type="submit" class="btn btn-temple">Save</button></div></form></div></div></div>
{% endblock %}
"""

USER_MANAGEMENT_TEMPLATE = """
{% extends "main" %}
{% block content %}
<div class="content-card">
    <div class="d-flex justify-content-between align-items-center mb-3"><h5 class="mb-0"><i class="fas fa-user-shield"></i> Users</h5><button class="btn btn-temple" data-bs-toggle="modal" data-bs-target="#auM"><i class="fas fa-plus"></i> Add</button></div>
    <table class="table table-hover"><thead><tr><th>#</th><th>Username</th><th>Name</th><th>Role</th><th>Status</th><th>Act</th></tr></thead>
    <tbody>{% for u in users %}<tr><td>{{ u.id }}</td><td>{{ u.username }}</td><td>{{ u.full_name or '-' }}</td><td><span class="badge {{ 'bg-danger' if u.role=='admin' else 'bg-primary' }}">{{ u.role }}</span></td><td><span class="badge {{ 'bg-success' if u.is_active_user else 'bg-secondary' }}">{{ 'Active' if u.is_active_user else 'Inactive' }}</span></td><td>{% if u.id!=current_user.id %}<form method="POST" action="{{ url_for('toggle_user',id=u.id) }}" style="display:inline"><button class="btn btn-sm {{ 'btn-warning' if u.is_active_user else 'btn-success' }}">{{ 'Deactivate' if u.is_active_user else 'Activate' }}</button></form>{% endif %}</td></tr>{% endfor %}</tbody></table>
</div>
<div class="modal fade" id="auM" tabindex="-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header" style="background:#8B0000;color:#FFD700;"><h5>Add User</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div><form method="POST" action="{{ url_for('add_user') }}"><div class="modal-body"><div class="mb-3"><label class="form-label">Username *</label><input type="text" name="username" class="form-control" required></div><div class="mb-3"><label class="form-label">Full Name</label><input type="text" name="full_name" class="form-control"></div><div class="mb-3"><label class="form-label">Password *</label><input type="password" name="password" class="form-control" required></div><div class="mb-3"><label class="form-label">Role</label><select name="role" class="form-select"><option value="user">User</option><option value="admin">Admin</option></select></div></div><div class="modal-footer"><button type="submit" class="btn btn-temple">Create</button></div></form></div></div></div>
{% endblock %}
"""

DELETED_BILLS_TEMPLATE = """
{% extends "main" %}
{% block content %}
<div class="content-card">
    <h5><i class="fas fa-trash-restore"></i> Deleted Bills (Admin View)</h5>
    <div class="table-responsive"><table class="table table-hover data-table">
        <thead><tr><th>Bill No</th><th>Date</th><th>Name</th><th>Amount</th><th>Deleted By</th><th>Deleted At</th><th>Reason</th></tr></thead>
        <tbody>{% for b in bills %}<tr>
            <td>{{ b.bill_number }}</td><td>{{ b.bill_date.strftime('%d/%m/%Y') }}</td>
            <td>{{ b.devotee.name if b.devotee else b.guest_name }}</td>
            <td>₹{{ '{:,.2f}'.format(b.amount) }}</td>
            <td>{% if b.deleted_by %}{{ users_map.get(b.deleted_by,'Unknown') }}{% else %}-{% endif %}</td>
            <td>{{ b.deleted_at.strftime('%d/%m/%Y %I:%M %p') if b.deleted_at else '-' }}</td>
            <td>{{ b.delete_reason or '-' }}</td>
        </tr>{% endfor %}</tbody>
    </table></div>
</div>
{% endblock %}
"""

UPLOAD_IMAGES_TEMPLATE = """
{% extends "main" %}
{% block content %}
<div class="content-card">
    <h5><i class="fas fa-image"></i> Upload Temple Images</h5>
    <p class="text-muted">Upload Amman image (round icon) and Temple background (login page).</p>
    <div class="row">
        <div class="col-md-6">
            <div class="content-card">
                <h6 style="color:#8B0000;">Amman Image (Round Icon)</h6>
                <div class="text-center mb-3"><img src="{{ amman_image }}" style="width:100px;height:100px;border-radius:50%;border:3px solid #FFD700;object-fit:cover;"></div>
                <form method="POST" enctype="multipart/form-data" action="{{ url_for('upload_amman') }}">
                    <div class="mb-3"><input type="file" name="amman_image" class="form-control" accept="image/*" required></div>
                    <button type="submit" class="btn btn-temple"><i class="fas fa-upload"></i> Upload Amman Image</button>
                </form>
                <small class="text-muted mt-2 d-block">Save as: uploads/temple/amman.png or .jpg</small>
            </div>
        </div>
        <div class="col-md-6">
            <div class="content-card">
                <h6 style="color:#8B0000;">Temple Background (Login Page)</h6>
                <div class="text-center mb-3">
                    {% if temple_bg %}<img src="{{ temple_bg }}" style="width:200px;height:120px;border-radius:8px;object-fit:cover;">{% else %}<div style="width:200px;height:120px;background:#ddd;border-radius:8px;display:flex;align-items:center;justify-content:center;margin:auto;"><i class="fas fa-image fa-2x text-muted"></i></div>{% endif %}
                </div>
                <form method="POST" enctype="multipart/form-data" action="{{ url_for('upload_temple_bg') }}">
                    <div class="mb-3"><input type="file" name="temple_bg" class="form-control" accept="image/*" required></div>
                    <button type="submit" class="btn btn-temple"><i class="fas fa-upload"></i> Upload Background</button>
                </form>
                <small class="text-muted mt-2 d-block">Save as: uploads/temple/temple_bg.jpg</small>
            </div>
        </div>
    </div>
</div>
{% endblock %}
"""

# Register all templates
TEMPLATES = {
    'main': MAIN_TEMPLATE,
    'login': LOGIN_TEMPLATE,
    'dashboard': DASHBOARD_TEMPLATE,
    'devotees': DEVOTEES_TEMPLATE,
    'add_devotee': ADD_DEVOTEE_TEMPLATE,
    'view_devotee': VIEW_DEVOTEE_TEMPLATE,
    'billing': BILLING_TEMPLATE,
    'new_bill': NEW_BILL_TEMPLATE,
    'view_bill': VIEW_BILL_TEMPLATE,
    'bill_pdf_tpl': BILL_PDF_TEMPLATE,
    'expenses': EXPENSES_TEMPLATE,
    'reports': REPORTS_TEMPLATE,
    'samaya': SAMAYA_TEMPLATE,
    'add_samaya': ADD_SAMAYA_TEMPLATE,
    'mandapam': MANDAPAM_TEMPLATE,
    'add_mandapam': ADD_MANDAPAM_TEMPLATE,
    'daily_pooja': DAILY_POOJA_TEMPLATE,
    'settings': SETTINGS_TEMPLATE,
    'user_management': USER_MANAGEMENT_TEMPLATE,
    'deleted_bills': DELETED_BILLS_TEMPLATE,
    'upload_images': UPLOAD_IMAGES_TEMPLATE,
}

app.jinja_loader = DictLoader(TEMPLATES)


# ============================================================
# ROUTES
# ============================================================

@app.route('/uploads/<folder>/<filename>')
def uploaded_file(folder, filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], folder, filename))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        u = User.query.filter_by(username=request.form.get('username')).first()
        if u and u.check_password(request.form.get('password')) and u.is_active_user:
            login_user(u)
            flash('Welcome back!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid credentials!', 'danger')
    return render_template_string(LOGIN_TEMPLATE)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/')
@login_required
def dashboard():
    period = request.args.get('period', 'daily')
    today_d = date.today()
    if period == 'daily':
        sd, ed = today_d, today_d
    elif period == 'weekly':
        sd, ed = today_d - timedelta(days=today_d.weekday()), today_d
    elif period == 'monthly':
        sd, ed = today_d.replace(day=1), today_d
    else:
        sd, ed = today_d.replace(month=1, day=1), today_d

    sdt = datetime.combine(sd, datetime.min.time())
    edt = datetime.combine(ed, datetime.max.time())

    ti = db.session.query(db.func.sum(Bill.amount)).filter(Bill.is_deleted==False, Bill.bill_date>=sdt, Bill.bill_date<=edt).scalar() or 0
    te = db.session.query(db.func.sum(Expense.amount)).filter(Expense.expense_date>=sd, Expense.expense_date<=ed).scalar() or 0
    td = Devotee.query.filter_by(is_family_head=True, is_active=True).count()
    tb = Bill.query.filter(Bill.is_deleted==False, Bill.bill_date>=sdt, Bill.bill_date<=edt).count()
    dp = DailyPooja.query.filter_by(is_active=True).all()
    bdays = Devotee.query.filter(Devotee.is_active==True, db.extract('month',Devotee.dob)==today_d.month, db.extract('day',Devotee.dob)==today_d.day).all()
    ticker = [f"Happy Birthday {d.name}! 🎂" for d in bdays]
    rb = Bill.query.filter_by(is_deleted=False).order_by(Bill.bill_date.desc()).limit(10).all()

    return render_template_string(DASHBOARD_TEMPLATE, page_title='Dashboard', period=period,
        total_income=ti, total_expenses=te, total_devotees=td, total_bills=tb,
        daily_poojas=dp, birthdays=bdays, ticker_messages=ticker, recent_bills=rb)


# ---- DEVOTEES ----
@app.route('/devotees')
@login_required
def devotees():
    dl = Devotee.query.filter_by(is_family_head=True, is_active=True).order_by(Devotee.name).all()
    return render_template_string(DEVOTEES_TEMPLATE, page_title='Devotees', devotees=dl)


@app.route('/devotees/add', methods=['GET','POST'])
@login_required
def add_devotee():
    pts = PoojaType.query.filter_by(is_active=True).all()
    if request.method == 'POST':
        d = Devotee()
        d.name = request.form.get('name')
        d.dob = datetime.strptime(request.form.get('dob'),'%Y-%m-%d').date() if request.form.get('dob') else None
        d.relation_type = request.form.get('relation_type')
        d.mobile_no = request.form.get('mobile_no')
        d.whatsapp_no = request.form.get('whatsapp_no')
        d.wedding_day = datetime.strptime(request.form.get('wedding_day'),'%Y-%m-%d').date() if request.form.get('wedding_day') else None
        d.natchathiram = request.form.get('natchathiram')
        d.address = request.form.get('address')
        d.is_family_head = True
        if 'photo' in request.files and request.files['photo'].filename:
            photo = request.files['photo']
            fn = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{photo.filename}")
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'],'devotees',fn))
            d.photo_filename = fn
        db.session.add(d); db.session.flush()

        # Family members
        fnames = request.form.getlist('fm_name[]')
        fdobs = request.form.getlist('fm_dob[]')
        frels = request.form.getlist('fm_relation[]')
        fnats = request.form.getlist('fm_natchathiram[]')
        fmobs = request.form.getlist('fm_mobile[]')
        for i in range(len(fnames)):
            if fnames[i].strip():
                fm = Devotee(name=fnames[i], is_family_head=False, family_head_id=d.id, address=d.address)
                fm.dob = datetime.strptime(fdobs[i],'%Y-%m-%d').date() if i<len(fdobs) and fdobs[i] else None
                fm.relation_type = frels[i] if i<len(frels) else None
                fm.natchathiram = fnats[i] if i<len(fnats) else None
                fm.mobile_no = fmobs[i] if i<len(fmobs) else None
                db.session.add(fm)

        # Yearly poojas
        ypt = request.form.getlist('yp_pooja_type[]')
        ypd = request.form.getlist('yp_date[]')
        ypn = request.form.getlist('yp_notes[]')
        for i in range(len(ypt)):
            if ypt[i] or (i<len(ypd) and ypd[i]):
                yp = DevoteeYearlyPooja(devotee_id=d.id)
                yp.pooja_type_id = int(ypt[i]) if ypt[i] else None
                yp.pooja_date = datetime.strptime(ypd[i],'%Y-%m-%d').date() if i<len(ypd) and ypd[i] else None
                yp.notes = ypn[i] if i<len(ypn) else None
                if yp.pooja_type_id:
                    pt = PoojaType.query.get(yp.pooja_type_id)
                    if pt: yp.pooja_name = pt.name
                db.session.add(yp)
        db.session.commit()
        flash('Devotee added!','success')
        return redirect(url_for('devotees'))
    return render_template_string(ADD_DEVOTEE_TEMPLATE, page_title='Add Devotee', devotee=None,
        pooja_types=pts, natchathiram_list=NATCHATHIRAM_LIST, relation_types=RELATION_TYPES)


@app.route('/devotees/edit/<int:id>', methods=['GET','POST'])
@login_required
def edit_devotee(id):
    d = Devotee.query.get_or_404(id)
    pts = PoojaType.query.filter_by(is_active=True).all()
    if request.method == 'POST':
        d.name = request.form.get('name')
        d.dob = datetime.strptime(request.form.get('dob'),'%Y-%m-%d').date() if request.form.get('dob') else None
        d.relation_type = request.form.get('relation_type')
        d.mobile_no = request.form.get('mobile_no')
        d.whatsapp_no = request.form.get('whatsapp_no')
        d.wedding_day = datetime.strptime(request.form.get('wedding_day'),'%Y-%m-%d').date() if request.form.get('wedding_day') else None
        d.natchathiram = request.form.get('natchathiram')
        d.address = request.form.get('address')
        if 'photo' in request.files and request.files['photo'].filename:
            photo = request.files['photo']
            fn = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{photo.filename}")
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'],'devotees',fn))
            d.photo_filename = fn

        # Family
        existing_ids = [fm.id for fm in d.family_members.all()]
        sub_ids = request.form.getlist('fm_id[]')
        fnames = request.form.getlist('fm_name[]')
        fdobs = request.form.getlist('fm_dob[]')
        frels = request.form.getlist('fm_relation[]')
        fnats = request.form.getlist('fm_natchathiram[]')
        fmobs = request.form.getlist('fm_mobile[]')
        kept = [int(x) for x in sub_ids if x!='new' and x]
        for fid in existing_ids:
            if fid not in kept:
                fm = Devotee.query.get(fid)
                if fm: db.session.delete(fm)
        for i in range(len(fnames)):
            if fnames[i].strip():
                if i<len(sub_ids) and sub_ids[i]!='new' and sub_ids[i]:
                    fm = Devotee.query.get(int(sub_ids[i]))
                    if fm:
                        fm.name=fnames[i]
                        fm.dob=datetime.strptime(fdobs[i],'%Y-%m-%d').date() if fdobs[i] else None
                        fm.relation_type=frels[i] if i<len(frels) else None
                        fm.natchathiram=fnats[i] if i<len(fnats) else None
                        fm.mobile_no=fmobs[i] if i<len(fmobs) else None
                else:
                    fm = Devotee(name=fnames[i], is_family_head=False, family_head_id=d.id, address=d.address)
                    fm.dob=datetime.strptime(fdobs[i],'%Y-%m-%d').date() if i<len(fdobs) and fdobs[i] else None
                    fm.relation_type=frels[i] if i<len(frels) else None
                    fm.natchathiram=fnats[i] if i<len(fnats) else None
                    fm.mobile_no=fmobs[i] if i<len(fmobs) else None
                    db.session.add(fm)

        # Yearly poojas
        DevoteeYearlyPooja.query.filter_by(devotee_id=d.id).delete()
        ypt = request.form.getlist('yp_pooja_type[]')
        ypd = request.form.getlist('yp_date[]')
        ypn = request.form.getlist('yp_notes[]')
        for i in range(len(ypt)):
            if ypt[i] or (i<len(ypd) and ypd[i]):
                yp = DevoteeYearlyPooja(devotee_id=d.id)
                yp.pooja_type_id=int(ypt[i]) if ypt[i] else None
                yp.pooja_date=datetime.strptime(ypd[i],'%Y-%m-%d').date() if i<len(ypd) and ypd[i] else None
                yp.notes=ypn[i] if i<len(ypn) else None
                if yp.pooja_type_id:
                    pt = PoojaType.query.get(yp.pooja_type_id)
                    if pt: yp.pooja_name=pt.name
                db.session.add(yp)
        db.session.commit()
        flash('Devotee updated!','success')
        return redirect(url_for('devotees'))
    return render_template_string(ADD_DEVOTEE_TEMPLATE, page_title='Edit Devotee', devotee=d,
        pooja_types=pts, natchathiram_list=NATCHATHIRAM_LIST, relation_types=RELATION_TYPES)


@app.route('/devotees/view/<int:id>')
@login_required
def view_devotee(id):
    d = Devotee.query.get_or_404(id)
    return render_template_string(VIEW_DEVOTEE_TEMPLATE, page_title='View Devotee', devotee=d)


@app.route('/devotees/delete/<int:id>', methods=['POST'])
@login_required
def delete_devotee(id):
    d = Devotee.query.get_or_404(id)
    for fm in d.family_members.all(): db.session.delete(fm)
    db.session.delete(d); db.session.commit()
    flash('Devotee deleted!','success')
    return redirect(url_for('devotees'))


# ---- BILLING ----
@app.route('/billing')
@login_required
def billing():
    fd = request.args.get('from_date', date.today().strftime('%Y-%m-%d'))
    td = request.args.get('to_date', date.today().strftime('%Y-%m-%d'))
    q = Bill.query
    if fd: q = q.filter(Bill.bill_date >= datetime.strptime(fd,'%Y-%m-%d'))
    if td: q = q.filter(Bill.bill_date <= datetime.combine(datetime.strptime(td,'%Y-%m-%d').date(), datetime.max.time()))
    bills = q.order_by(Bill.bill_date.desc()).all()
    return render_template_string(BILLING_TEMPLATE, page_title='Billing', bills=bills, from_date=fd, to_date=td)


@app.route('/billing/new', methods=['GET','POST'])
@login_required
def new_bill():
    pts = PoojaType.query.filter_by(is_active=True).all()
    dl = Devotee.query.filter_by(is_family_head=True, is_active=True).order_by(Devotee.name).all()
    lb = Bill.query.order_by(Bill.id.desc()).first()
    nbn = f"BILL-{(lb.id+1) if lb else 1:06d}"
    if request.method == 'POST':
        b = Bill()
        b.bill_number = request.form.get('bill_number')
        b.manual_bill_no = request.form.get('manual_bill_no')
        b.bill_book_no = request.form.get('bill_book_no')
        bds = request.form.get('bill_date')
        b.bill_date = datetime.strptime(bds,'%Y-%m-%dT%H:%M') if bds else datetime.utcnow()
        b.devotee_type = request.form.get('devotee_type')
        if b.devotee_type == 'enrolled':
            b.devotee_id = int(request.form.get('devotee_id')) if request.form.get('devotee_id') else None
        else:
            b.guest_name = request.form.get('guest_name')
            b.guest_address = request.form.get('guest_address')
            b.guest_mobile = request.form.get('guest_mobile')
            b.guest_whatsapp = request.form.get('guest_whatsapp')
        b.pooja_type_id = int(request.form.get('pooja_type_id')) if request.form.get('pooja_type_id') else None
        b.amount = float(request.form.get('amount',0))
        b.notes = request.form.get('notes')
        b.created_by = current_user.id
        db.session.add(b); db.session.commit()
        flash('Bill created!','success')
        return redirect(url_for('view_bill', id=b.id))
    return render_template_string(NEW_BILL_TEMPLATE, page_title='New Bill', pooja_types=pts, devotees_list=dl, next_bill_no=nbn)


@app.route('/billing/view/<int:id>')
@login_required
def view_bill(id):
    b = Bill.query.get_or_404(id)
    return render_template_string(VIEW_BILL_TEMPLATE, page_title='View Bill', bill=b)


@app.route('/billing/pdf/<int:id>')
@login_required
def bill_pdf(id):
    b = Bill.query.get_or_404(id)
    html = render_template_string(BILL_PDF_TEMPLATE, bill=b, amman_image=get_amman_image(),
        temple_name=TEMPLE_NAME, temple_trust=TEMPLE_TRUST,
        temple_address_line3=TEMPLE_ADDRESS_LINE3, temple_full_address=TEMPLE_FULL_ADDRESS)

    # Try to generate PDF using weasyprint or xhtml2pdf, fallback to HTML
    try:
        from xhtml2pdf import pisa
        pdf_buffer = BytesIO()
        pisa.CreatePDF(BytesIO(html.encode('utf-8')), dest=pdf_buffer)
        pdf_buffer.seek(0)
        return send_file(pdf_buffer, mimetype='application/pdf',
                        download_name=f'Bill_{b.bill_number}.pdf', as_attachment=True)
    except ImportError:
        try:
            from weasyprint import HTML
            pdf_buffer = BytesIO()
            HTML(string=html).write_pdf(pdf_buffer)
            pdf_buffer.seek(0)
            return send_file(pdf_buffer, mimetype='application/pdf',
                            download_name=f'Bill_{b.bill_number}.pdf', as_attachment=True)
        except ImportError:
            # Fallback: return as printable HTML
            response = make_response(html)
            response.headers['Content-Type'] = 'text/html'
            return response


@app.route('/billing/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_bill(id):
    b = Bill.query.get_or_404(id)
    b.is_deleted = True
    b.deleted_by = current_user.id
    b.deleted_at = datetime.utcnow()
    b.delete_reason = request.form.get('delete_reason','No reason given')
    db.session.commit()
    flash(f'Bill {b.bill_number} deleted!','success')
    return redirect(url_for('billing'))


@app.route('/billing/deleted')
@login_required
@admin_required
def deleted_bills():
    bills = Bill.query.filter_by(is_deleted=True).order_by(Bill.deleted_at.desc()).all()
    um = {u.id: u.full_name or u.username for u in User.query.all()}
    return render_template_string(DELETED_BILLS_TEMPLATE, page_title='Deleted Bills', bills=bills, users_map=um)


# ---- EXPENSES ----
@app.route('/expenses')
@login_required
def expenses_page():
    fd = request.args.get('from_date', date.today().replace(day=1).strftime('%Y-%m-%d'))
    td = request.args.get('to_date', date.today().strftime('%Y-%m-%d'))
    q = Expense.query
    if fd: q = q.filter(Expense.expense_date >= datetime.strptime(fd,'%Y-%m-%d').date())
    if td: q = q.filter(Expense.expense_date <= datetime.strptime(td,'%Y-%m-%d').date())
    exps = q.order_by(Expense.expense_date.desc()).all()
    ets = ExpenseType.query.filter_by(is_active=True).all()
    return render_template_string(EXPENSES_TEMPLATE, page_title='Expenses', expenses=exps,
        expense_types=ets, from_date=fd, to_date=td, today=date.today().strftime('%Y-%m-%d'))


@app.route('/expenses/add', methods=['POST'])
@login_required
def add_expense():
    e = Expense()
    e.expense_type_id = int(request.form.get('expense_type_id')) if request.form.get('expense_type_id') else None
    e.amount = float(request.form.get('amount',0))
    e.description = request.form.get('description')
    e.expense_date = datetime.strptime(request.form.get('expense_date'),'%Y-%m-%d').date() if request.form.get('expense_date') else date.today()
    e.created_by = current_user.id
    db.session.add(e); db.session.commit()
    flash('Expense added!','success')
    return redirect(url_for('expenses_page'))


@app.route('/expenses/delete/<int:id>', methods=['POST'])
@login_required
def delete_expense(id):
    e = Expense.query.get_or_404(id)
    db.session.delete(e); db.session.commit()
    flash('Expense deleted!','success')
    return redirect(url_for('expenses_page'))


# ---- REPORTS ----
@app.route('/reports')
@login_required
def reports():
    fd = request.args.get('from_date', date.today().replace(day=1).strftime('%Y-%m-%d'))
    td = request.args.get('to_date', date.today().strftime('%Y-%m-%d'))
    s = datetime.strptime(fd,'%Y-%m-%d')
    e = datetime.combine(datetime.strptime(td,'%Y-%m-%d').date(), datetime.max.time())
    ti = db.session.query(db.func.sum(Bill.amount)).filter(Bill.is_deleted==False, Bill.bill_date>=s, Bill.bill_date<=e).scalar() or 0
    te = db.session.query(db.func.sum(Expense.amount)).filter(Expense.expense_date>=s.date(), Expense.expense_date<=e.date()).scalar() or 0
    ibp = db.session.query(PoojaType.name, db.func.count(Bill.id), db.func.sum(Bill.amount)).join(Bill, Bill.pooja_type_id==PoojaType.id).filter(Bill.is_deleted==False, Bill.bill_date>=s, Bill.bill_date<=e).group_by(PoojaType.name).all()
    ibp = [{'name':r[0],'count':r[1],'total':r[2] or 0} for r in ibp]
    ebt = db.session.query(ExpenseType.name, db.func.count(Expense.id), db.func.sum(Expense.amount)).join(Expense, Expense.expense_type_id==ExpenseType.id).filter(Expense.expense_date>=s.date(), Expense.expense_date<=e.date()).group_by(ExpenseType.name).all()
    ebt = [{'name':r[0],'count':r[1],'total':r[2] or 0} for r in ebt]
    return render_template_string(REPORTS_TEMPLATE, page_title='Reports', from_date=fd, to_date=td,
        total_income=ti, total_expenses=te, income_by_pooja=ibp, expenses_by_type=ebt)


# ---- SAMAYA VAKUPPU ----
@app.route('/samaya')
@login_required
def samaya_vakuppu():
    return render_template_string(SAMAYA_TEMPLATE, page_title='Samaya Vakuppu',
        students=SamayaVakuppu.query.order_by(SamayaVakuppu.student_name).all())


@app.route('/samaya/add', methods=['GET','POST'])
@login_required
def add_samaya():
    if request.method == 'POST':
        s = SamayaVakuppu()
        s.student_name=request.form.get('student_name')
        s.dob=datetime.strptime(request.form.get('dob'),'%Y-%m-%d').date() if request.form.get('dob') else None
        s.address=request.form.get('address')
        s.father_mother_name=request.form.get('father_mother_name')
        s.bond_no=request.form.get('bond_no')
        s.bond_issue_date=datetime.strptime(request.form.get('bond_issue_date'),'%Y-%m-%d').date() if request.form.get('bond_issue_date') else None
        s.bond_issuing_bank=request.form.get('bond_issuing_bank')
        s.branch_of_bank=request.form.get('branch_of_bank')
        for fld, attr in [('photo','photo_filename'),('bond_scan','bond_scan_filename')]:
            if fld in request.files and request.files[fld].filename:
                f = request.files[fld]
                fn = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{fld}_{f.filename}")
                f.save(os.path.join(app.config['UPLOAD_FOLDER'],'samaya',fn))
                setattr(s, attr, fn)
        db.session.add(s); db.session.commit()
        flash('Student added!','success')
        return redirect(url_for('samaya_vakuppu'))
    return render_template_string(ADD_SAMAYA_TEMPLATE, page_title='Add Student', student=None)


@app.route('/samaya/edit/<int:id>', methods=['GET','POST'])
@login_required
def edit_samaya(id):
    s = SamayaVakuppu.query.get_or_404(id)
    if request.method == 'POST':
        s.student_name=request.form.get('student_name')
        s.dob=datetime.strptime(request.form.get('dob'),'%Y-%m-%d').date() if request.form.get('dob') else None
        s.address=request.form.get('address')
        s.father_mother_name=request.form.get('father_mother_name')
        s.bond_no=request.form.get('bond_no')
        s.bond_issue_date=datetime.strptime(request.form.get('bond_issue_date'),'%Y-%m-%d').date() if request.form.get('bond_issue_date') else None
        s.bond_issuing_bank=request.form.get('bond_issuing_bank')
        s.branch_of_bank=request.form.get('branch_of_bank')
        for fld, attr in [('photo','photo_filename'),('bond_scan','bond_scan_filename')]:
            if fld in request.files and request.files[fld].filename:
                f = request.files[fld]
                fn = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{fld}_{f.filename}")
                f.save(os.path.join(app.config['UPLOAD_FOLDER'],'samaya',fn))
                setattr(s, attr, fn)
        db.session.commit()
        flash('Updated!','success')
        return redirect(url_for('samaya_vakuppu'))
    return render_template_string(ADD_SAMAYA_TEMPLATE, page_title='Edit Student', student=s)


@app.route('/samaya/delete/<int:id>', methods=['POST'])
@login_required
def delete_samaya(id):
    db.session.delete(SamayaVakuppu.query.get_or_404(id)); db.session.commit()
    flash('Deleted!','success')
    return redirect(url_for('samaya_vakuppu'))


# ---- THIRUMANA MANDAPAM ----
@app.route('/mandapam')
@login_required
def thirumana_mandapam():
    return render_template_string(MANDAPAM_TEMPLATE, page_title='Thirumana Mandapam',
        records=ThirumanaMandapam.query.order_by(ThirumanaMandapam.name).all())


@app.route('/mandapam/add', methods=['GET','POST'])
@login_required
def add_mandapam():
    if request.method == 'POST':
        m = ThirumanaMandapam()
        m.name=request.form.get('name'); m.address=request.form.get('address')
        m.bond_no=request.form.get('bond_no')
        m.bond_issued_date=datetime.strptime(request.form.get('bond_issued_date'),'%Y-%m-%d').date() if request.form.get('bond_issued_date') else None
        m.amount=float(request.form.get('amount',0)); m.no_of_bond=int(request.form.get('no_of_bond',1))
        for fld, attr in [('photo','photo_filename'),('bond_scan','bond_scan_filename')]:
            if fld in request.files and request.files[fld].filename:
                f = request.files[fld]
                fn = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{fld}_{f.filename}")
                f.save(os.path.join(app.config['UPLOAD_FOLDER'],'mandapam',fn))
                setattr(m, attr, fn)
        db.session.add(m); db.session.commit()
        flash('Added!','success')
        return redirect(url_for('thirumana_mandapam'))
    return render_template_string(ADD_MANDAPAM_TEMPLATE, page_title='Add Record', record=None)


@app.route('/mandapam/edit/<int:id>', methods=['GET','POST'])
@login_required
def edit_mandapam(id):
    m = ThirumanaMandapam.query.get_or_404(id)
    if request.method == 'POST':
        m.name=request.form.get('name'); m.address=request.form.get('address')
        m.bond_no=request.form.get('bond_no')
        m.bond_issued_date=datetime.strptime(request.form.get('bond_issued_date'),'%Y-%m-%d').date() if request.form.get('bond_issued_date') else None
        m.amount=float(request.form.get('amount',0)); m.no_of_bond=int(request.form.get('no_of_bond',1))
        for fld, attr in [('photo','photo_filename'),('bond_scan','bond_scan_filename')]:
            if fld in request.files and request.files[fld].filename:
                f = request.files[fld]
                fn = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{fld}_{f.filename}")
                f.save(os.path.join(app.config['UPLOAD_FOLDER'],'mandapam',fn))
                setattr(m, attr, fn)
        db.session.commit()
        flash('Updated!','success')
        return redirect(url_for('thirumana_mandapam'))
    return render_template_string(ADD_MANDAPAM_TEMPLATE, page_title='Edit Record', record=m)


@app.route('/mandapam/delete/<int:id>', methods=['POST'])
@login_required
def delete_mandapam(id):
    db.session.delete(ThirumanaMandapam.query.get_or_404(id)); db.session.commit()
    flash('Deleted!','success')
    return redirect(url_for('thirumana_mandapam'))


# ---- DAILY POOJA ----
@app.route('/daily-pooja')
@login_required
def daily_pooja_page():
    return render_template_string(DAILY_POOJA_TEMPLATE, page_title='Daily Pooja',
        poojas=DailyPooja.query.filter_by(is_active=True).order_by(DailyPooja.pooja_time).all())


@app.route('/daily-pooja/add', methods=['POST'])
@login_required
def add_daily_pooja():
    dp = DailyPooja(pooja_name=request.form.get('pooja_name'), pooja_time=request.form.get('pooja_time'), description=request.form.get('description'))
    db.session.add(dp); db.session.commit()
    flash('Added!','success')
    return redirect(url_for('daily_pooja_page'))


@app.route('/daily-pooja/delete/<int:id>', methods=['POST'])
@login_required
def delete_daily_pooja(id):
    dp = DailyPooja.query.get_or_404(id); dp.is_active=False; db.session.commit()
    flash('Removed!','success')
    return redirect(url_for('daily_pooja_page'))


# ---- SETTINGS ----
@app.route('/settings')
@login_required
def settings():
    return render_template_string(SETTINGS_TEMPLATE, page_title='Settings',
        pooja_types=PoojaType.query.filter_by(is_active=True).all(),
        expense_types=ExpenseType.query.filter_by(is_active=True).all())


@app.route('/settings/pooja-type/add', methods=['POST'])
@login_required
def add_pooja_type():
    db.session.add(PoojaType(name=request.form.get('name'), amount=float(request.form.get('amount',0))))
    db.session.commit(); flash('Added!','success')
    return redirect(url_for('settings'))


@app.route('/settings/pooja-type/delete/<int:id>', methods=['POST'])
@login_required
def delete_pooja_type(id):
    PoojaType.query.get_or_404(id).is_active=False; db.session.commit()
    flash('Removed!','success')
    return redirect(url_for('settings'))


@app.route('/settings/expense-type/add', methods=['POST'])
@login_required
def add_expense_type():
    db.session.add(ExpenseType(name=request.form.get('name')))
    db.session.commit(); flash('Added!','success')
    return redirect(url_for('settings'))


@app.route('/settings/expense-type/delete/<int:id>', methods=['POST'])
@login_required
def delete_expense_type(id):
    ExpenseType.query.get_or_404(id).is_active=False; db.session.commit()
    flash('Removed!','success')
    return redirect(url_for('settings'))


# ---- USER MANAGEMENT ----
@app.route('/users')
@login_required
@admin_required
def user_management():
    return render_template_string(USER_MANAGEMENT_TEMPLATE, page_title='Users', users=User.query.all())


@app.route('/users/add', methods=['POST'])
@login_required
@admin_required
def add_user():
    un = request.form.get('username')
    if User.query.filter_by(username=un).first():
        flash('Username exists!','danger')
        return redirect(url_for('user_management'))
    u = User(username=un, full_name=request.form.get('full_name'), role=request.form.get('role','user'))
    u.set_password(request.form.get('password'))
    db.session.add(u); db.session.commit()
    flash('User created!','success')
    return redirect(url_for('user_management'))


@app.route('/users/toggle/<int:id>', methods=['POST'])
@login_required
@admin_required
def toggle_user(id):
    u = User.query.get_or_404(id); u.is_active_user=not u.is_active_user; db.session.commit()
    flash(f'User {"activated" if u.is_active_user else "deactivated"}!','success')
    return redirect(url_for('user_management'))


# ---- TEMPLE IMAGE UPLOAD ----
@app.route('/temple-images')
@login_required
def upload_temple_images():
    return render_template_string(UPLOAD_IMAGES_TEMPLATE, page_title='Temple Images')


@app.route('/temple-images/amman', methods=['POST'])
@login_required
def upload_amman():
    if 'amman_image' in request.files and request.files['amman_image'].filename:
        f = request.files['amman_image']
        ext = f.filename.rsplit('.',1)[-1].lower() if '.' in f.filename else 'png'
        # Remove old files
        for old_ext in ['png','jpg','jpeg','webp']:
            old_path = os.path.join(app.config['UPLOAD_FOLDER'],'temple',f'amman.{old_ext}')
            if os.path.exists(old_path): os.remove(old_path)
        fn = f'amman.{ext}'
        f.save(os.path.join(app.config['UPLOAD_FOLDER'],'temple',fn))
        flash('Amman image uploaded!','success')
    return redirect(url_for('upload_temple_images'))


@app.route('/temple-images/bg', methods=['POST'])
@login_required
def upload_temple_bg():
    if 'temple_bg' in request.files and request.files['temple_bg'].filename:
        f = request.files['temple_bg']
        ext = f.filename.rsplit('.',1)[-1].lower() if '.' in f.filename else 'jpg'
        for old_ext in ['png','jpg','jpeg','webp']:
            old_path = os.path.join(app.config['UPLOAD_FOLDER'],'temple',f'temple_bg.{old_ext}')
            if os.path.exists(old_path): os.remove(old_path)
        fn = f'temple_bg.{ext}'
        f.save(os.path.join(app.config['UPLOAD_FOLDER'],'temple',fn))
        flash('Temple background uploaded!','success')
    return redirect(url_for('upload_temple_images'))


# ---- API ----
@app.route('/api/devotee/<int:id>')
@login_required
def api_devotee(id):
    d = Devotee.query.get_or_404(id)
    return jsonify({'id':d.id,'name':d.name,'mobile_no':d.mobile_no,'address':d.address})


# ============================================================
# DATABASE INITIALIZATION
# ============================================================
def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            a = User(username='admin', full_name='Administrator', role='admin')
            a.set_password('admin123')
            db.session.add(a); db.session.commit()
            print("Admin created: admin / admin123")

        if PoojaType.query.count() == 0:
            for n, amt in [
                ('அபிஷேகம் (Abhishekam)',100),('அர்ச்சனை (Archanai)',50),
                ('சஹஸ்ரநாம அர்ச்சனை (Sahasranamam)',200),('திருவிளக்கு பூஜை (Thiruvilakku)',150),
                ('கணபதி ஹோமம் (Ganapathi Homam)',500),('நவக்கிரக பூஜை (Navagraha Pooja)',300),
                ('சந்தன கவசம் (Chandana Kavasam)',250),('அன்னதானம் (Annadhanam)',1000),
            ]:
                db.session.add(PoojaType(name=n, amount=amt))
            db.session.commit()

        if ExpenseType.query.count() == 0:
            for n in ['பூ (Flowers)','எண்ணெய் (Oil)','கற்பூரம் (Camphor)',
                       'மின்சாரம் (Electricity)','நிர்வாகம் (Admin)','பராமரிப்பு (Maintenance)',
                       'சம்பளம் (Salary)','இதர (Others)']:
                db.session.add(ExpenseType(name=n))
            db.session.commit()

        if DailyPooja.query.count() == 0:
            for n, t, d in [
                ('சுப்ரபாதம்','5:30 AM','Morning prayer'),('காலை அபிஷேகம்','6:00 AM','Morning bath'),
                ('காலை பூஜை','7:00 AM','Morning worship'),('உச்சிக்கால பூஜை','12:00 PM','Noon'),
                ('சாயரக்ஷை','6:00 PM','Evening'),('அர்த்த ஜாம பூஜை','8:00 PM','Night'),
            ]:
                db.session.add(DailyPooja(pooja_name=n, pooja_time=t, description=d))
            db.session.commit()


# ============================================================
# MAIN
# ============================================================
if __name__ == '__main__':
    init_db()
    print("\n" + "="*60)
    print("🕉️  TEMPLE MANAGEMENT SYSTEM")
    print(f"   {TEMPLE_NAME}")
    print(f"   {TEMPLE_TRUST}")
    print(f"   {TEMPLE_ADDRESS_LINE3}")
    print("="*60)
    print("   Login: admin / admin123")
    print("   URL: http://localhost:5000")
    print("="*60)
    print("\n📌 To add Amman image: place amman.png in uploads/temple/")
    print("📌 To add login bg: place temple_bg.jpg in uploads/temple/")
    print("📌 Or use Temple Images page in sidebar to upload\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
