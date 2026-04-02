"""
============================================================
🕉️ ARULMIGU BHADRESHWARI AMMAN KOVIL
   Temple Management System
   Streamlit + Supabase Version
============================================================
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
from supabase import create_client, Client
import bcrypt
import json
import base64
import os
from io import BytesIO
from PIL import Image
import time

# ============================================================
# PAGE CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="🕉️ Arulmigu Bhadreshwari Amman Kovil",
    page_icon="🕉️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# TEMPLE CONFIGURATION
# ============================================================
TEMPLE_NAME = "Arulmigu Bhadreshwari Amman Kovil"
TEMPLE_TRUST = "Samrakshana Seva Trust"
TEMPLE_REG = "179/2004"
TEMPLE_PLACE = "Kanjampuram"
TEMPLE_DISTRICT = "Kanniyakumari Dist- 629154"
TEMPLE_ADDRESS_LINE1 = f"{TEMPLE_NAME}"
TEMPLE_ADDRESS_LINE2 = f"{TEMPLE_TRUST} - {TEMPLE_REG}"
TEMPLE_ADDRESS_LINE3 = f"{TEMPLE_PLACE}, {TEMPLE_DISTRICT}"

# ============================================================
# CONSTANTS
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
    'Father-in-law', 'Mother-in-law', 'Son-in-law',
    'Daughter-in-law', 'Uncle', 'Aunt', 'Nephew', 'Niece',
    'Cousin', 'Other'
]

# ============================================================
# SUPABASE CONNECTION
# ============================================================
@st.cache_resource
def get_supabase_client():
    """Initialize Supabase client"""
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY", "")
    if not url or not key:
        st.error("⚠️ Supabase credentials not found! "
                 "Add SUPABASE_URL and SUPABASE_KEY to .streamlit/secrets.toml")
        st.stop()
    return create_client(url, key)


def get_db():
    """Get Supabase client"""
    return get_supabase_client()


# ============================================================
# PASSWORD UTILITIES
# ============================================================
def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')


def check_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(
            password.encode('utf-8'),
            hashed.encode('utf-8')
        )
    except Exception:
        return False


# ============================================================
# SESSION STATE INITIALIZATION
# ============================================================
def init_session_state():
    defaults = {
        'logged_in': False,
        'user_id': None,
        'username': '',
        'full_name': '',
        'role': 'user',
        'current_page': 'dashboard',
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ============================================================
# CUSTOM CSS
# ============================================================
def apply_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Tamil:wght@400;600;700&display=swap');

        .main-header {
            background: linear-gradient(135deg, #8B0000, #DC143C);
            color: #FFD700;
            padding: 15px 20px;
            border-radius: 12px;
            text-align: center;
            margin-bottom: 20px;
            box-shadow: 0 4px 15px rgba(139,0,0,0.3);
        }
        .main-header h1 {
            font-size: 1.5em;
            margin: 0;
            font-weight: 700;
        }
        .main-header p {
            font-size: 0.85em;
            margin: 2px 0 0 0;
            opacity: 0.9;
        }

        .stat-card {
            border-radius: 15px;
            padding: 20px;
            color: white;
            box-shadow: 0 5px 20px rgba(0,0,0,0.15);
            margin-bottom: 15px;
            position: relative;
            overflow: hidden;
        }
        .stat-card.income { background: linear-gradient(135deg, #228B22, #32CD32); }
        .stat-card.expense { background: linear-gradient(135deg, #DC143C, #FF4500); }
        .stat-card.devotees { background: linear-gradient(135deg, #4169E1, #6495ED); }
        .stat-card.bills { background: linear-gradient(135deg, #FF8C00, #FFD700); }
        .stat-card h6 { font-size: 0.85em; opacity: 0.9; margin-bottom: 5px; }
        .stat-card h3 { font-size: 1.8em; font-weight: 700; margin: 0; }

        .pooja-card {
            background: linear-gradient(135deg, #FFF8DC, #FFEFD5);
            border: 1px solid #FFD700;
            border-radius: 10px;
            padding: 12px;
            margin-bottom: 8px;
            border-left: 4px solid #8B0000;
        }

        .content-card {
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 15px rgba(0,0,0,0.08);
            padding: 20px;
            margin-bottom: 15px;
        }
        .content-card h5 {
            color: #8B0000;
            border-bottom: 2px solid #FFD700;
            padding-bottom: 8px;
            font-weight: 600;
        }

        .birthday-card {
            background: #FFF8DC;
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 8px;
            border-left: 3px solid #DC143C;
        }

        .news-ticker {
            background: linear-gradient(90deg, #8B0000, #DC143C, #8B0000);
            color: #FFD700;
            padding: 10px 15px;
            border-radius: 10px;
            margin-bottom: 18px;
            font-weight: 500;
            overflow: hidden;
            white-space: nowrap;
        }

        .sidebar .sidebar-content {
            background: linear-gradient(180deg, #8B0000 0%, #B22222 50%, #DC143C 100%);
        }

        div[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #8B0000 0%, #B22222 50%, #DC143C 100%);
        }
        div[data-testid="stSidebar"] .stMarkdown h1,
        div[data-testid="stSidebar"] .stMarkdown h2,
        div[data-testid="stSidebar"] .stMarkdown h3,
        div[data-testid="stSidebar"] .stMarkdown p,
        div[data-testid="stSidebar"] .stMarkdown span,
        div[data-testid="stSidebar"] .stMarkdown label {
            color: #FFD700 !important;
        }

        .stButton>button {
            background: linear-gradient(135deg, #8B0000, #DC143C);
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: 500;
            transition: all 0.3s;
        }
        .stButton>button:hover {
            background: linear-gradient(135deg, #DC143C, #FF4500);
            box-shadow: 0 4px 12px rgba(220,20,60,0.4);
        }

        .bill-header {
            text-align: center;
            border-bottom: 3px double #8B0000;
            padding-bottom: 12px;
            margin-bottom: 15px;
        }
        .bill-header h3 { color: #8B0000; margin: 0; font-weight: 700; }
        .bill-header h5 { color: #DC143C; margin: 2px 0; font-weight: 600; }
        .bill-header p { color: #555; font-size: 0.85em; margin: 1px 0; }

        .deleted-row { text-decoration: line-through; opacity: 0.5; }

        .login-container {
            max-width: 450px;
            margin: 50px auto;
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.15);
        }
    </style>
    """, unsafe_allow_html=True)


# ============================================================
# HELPER FUNCTIONS
# ============================================================
def generate_bill_number():
    """Generate unique bill number"""
    db = get_db()
    today = date.today()
    prefix = f"BILL-{today.strftime('%Y%m%d')}"
    result = db.table('bills').select('bill_number').like(
        'bill_number', f'{prefix}%'
    ).execute()
    count = len(result.data) + 1
    return f"{prefix}-{count:04d}"


def get_period_dates(period):
    """Get start and end dates for a period"""
    today = date.today()
    if period == 'daily':
        return today, today
    elif period == 'weekly':
        start = today - timedelta(days=today.weekday())
        return start, today
    elif period == 'monthly':
        start = today.replace(day=1)
        return start, today
    elif period == 'yearly':
        start = today.replace(month=1, day=1)
        return start, today
    return today, today


def upload_to_supabase_storage(file, bucket, filename):
    """Upload file to Supabase Storage"""
    db = get_db()
    try:
        file_bytes = file.read()
        db.storage.from_(bucket).upload(
            filename,
            file_bytes,
            {"content-type": file.type}
        )
        url = db.storage.from_(bucket).get_public_url(filename)
        return url
    except Exception as e:
        st.error(f"Upload error: {e}")
        return None


def format_currency(amount):
    """Format amount as Indian currency"""
    if amount is None:
        amount = 0
    return f"₹{amount:,.2f}"


# ============================================================
# AUTHENTICATION
# ============================================================
def login_page():
    """Login page"""
    st.markdown("""
        <div style="text-align:center; padding:20px;">
            <h1 style="color:#8B0000;">🕉️</h1>
            <h2 style="color:#8B0000; font-weight:700;">
                """ + TEMPLE_NAME + """
            </h2>
            <p style="color:#DC143C; font-weight:600;">
                """ + TEMPLE_ADDRESS_LINE2 + """
            </p>
            <p style="color:#666;">
                """ + TEMPLE_ADDRESS_LINE3 + """
            </p>
            <hr style="border-color:#FFD700;">
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🔐 Login")
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter username")
            password = st.text_input(
                "Password", type="password",
                placeholder="Enter password"
            )
            submitted = st.form_submit_button(
                "🔑 Login", use_container_width=True
            )

            if submitted:
                if not username or not password:
                    st.error("Please enter both username and password!")
                    return

                db = get_db()
                result = db.table('users').select('*').eq(
                    'username', username
                ).execute()

                if result.data:
                    user = result.data[0]
                    if check_password(password, user['password_hash']):
                        if user.get('is_active_user', True):
                            st.session_state['logged_in'] = True
                            st.session_state['user_id'] = user['id']
                            st.session_state['username'] = user['username']
                            st.session_state['full_name'] = (
                                user.get('full_name', '') or user['username']
                            )
                            st.session_state['role'] = (
                                user.get('role', 'user')
                            )
                            st.success("✅ Login successful!")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("❌ Account is deactivated!")
                    else:
                        st.error("❌ Invalid password!")
                else:
                    st.error("❌ User not found!")

        st.markdown("""
            <div style="text-align:center; margin-top:20px;">
                <small style="color:#aaa;">
                    🕉️ Temple Management System<br>
                    Default: admin / admin123
                </small>
            </div>
        """, unsafe_allow_html=True)


def create_default_admin():
    """Create default admin if not exists"""
    db = get_db()
    result = db.table('users').select('id').eq(
        'username', 'admin'
    ).execute()
    if not result.data:
        db.table('users').insert({
            'username': 'admin',
            'password_hash': hash_password('admin123'),
            'full_name': 'Temple Admin',
            'role': 'admin',
            'is_active_user': True
        }).execute()


# ============================================================
# SIDEBAR NAVIGATION
# ============================================================
def render_sidebar():
    """Render sidebar navigation"""
    with st.sidebar:
        st.markdown(f"""
            <div style="text-align:center; padding:10px;">
                <h3 style="color:#FFD700; margin:5px 0;">🕉️</h3>
                <h4 style="color:#FFD700; font-size:0.9em; margin:3px 0;">
                    {TEMPLE_NAME}
                </h4>
                <p style="color:rgba(255,215,0,0.7); font-size:0.7em;">
                    {TEMPLE_TRUST}
                </p>
                <p style="color:#FFD700; font-size:0.75em;">
                    👤 {st.session_state['full_name']}
                    {'🔑 ADMIN' if st.session_state['role'] == 'admin' else ''}
                </p>
                <hr style="border-color:rgba(255,215,0,0.3);">
            </div>
        """, unsafe_allow_html=True)

        menu_items = {
            "📊 Dashboard": "dashboard",
            "👥 Devotees": "devotees",
            "🧾 Billing": "billing",
            "💰 Expenses": "expenses",
            "📈 Reports": "reports",
            "---1": "divider",
            "🎓 Samaya Vakuppu": "samaya",
            "🏛️ Thirumana Mandapam": "mandapam",
            "---2": "divider",
            "🙏 Daily Pooja": "daily_pooja",
            "⚙️ Settings": "settings",
        }

        if st.session_state['role'] == 'admin':
            menu_items["👤 User Management"] = "users"
            menu_items["🗑️ Deleted Bills"] = "deleted_bills"

        menu_items["🚪 Logout"] = "logout"

        for label, page in menu_items.items():
            if page == "divider":
                st.markdown(
                    "<hr style='border-color:rgba(255,215,0,0.2);margin:5px 0;'>",
                    unsafe_allow_html=True
                )
                continue

            if st.button(
                label,
                key=f"nav_{page}",
                use_container_width=True
            ):
                if page == "logout":
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.rerun()
                else:
                    st.session_state['current_page'] = page
                    st.rerun()


# ============================================================
# DASHBOARD PAGE
# ============================================================
def dashboard_page():
    """Main dashboard"""
    db = get_db()

    # Header
    st.markdown(f"""
        <div class="main-header">
            <h1>🕉️ {TEMPLE_NAME}</h1>
            <p>{TEMPLE_ADDRESS_LINE2} | {TEMPLE_ADDRESS_LINE3}</p>
            <p>📅 {datetime.now().strftime('%d %B %Y, %A')}</p>
        </div>
    """, unsafe_allow_html=True)

    # Birthday ticker
    today = date.today()
    birthdays_result = db.table('devotees').select('name, mobile_no').eq(
        'is_active', True
    ).execute()

    birthday_names = []
    for d in birthdays_result.data:
        # We check birthdays in Python since Supabase
        # date filtering for month/day is complex
        pass

    # Period selector
    col1, col2, col3, col4 = st.columns(4)
    period = 'daily'
    with col1:
        if st.button("📅 Daily", use_container_width=True):
            st.session_state['dash_period'] = 'daily'
    with col2:
        if st.button("📆 Weekly", use_container_width=True):
            st.session_state['dash_period'] = 'weekly'
    with col3:
        if st.button("🗓️ Monthly", use_container_width=True):
            st.session_state['dash_period'] = 'monthly'
    with col4:
        if st.button("📊 Yearly", use_container_width=True):
            st.session_state['dash_period'] = 'yearly'

    period = st.session_state.get('dash_period', 'daily')
    start_date, end_date = get_period_dates(period)

    # Statistics
    bills_result = db.table('bills').select(
        'amount'
    ).eq('is_deleted', False).gte(
        'bill_date', start_date.isoformat()
    ).lte(
        'bill_date', end_date.isoformat() + "T23:59:59"
    ).execute()

    total_income = sum(b.get('amount', 0) or 0 for b in bills_result.data)
    total_bills = len(bills_result.data)

    expenses_result = db.table('expenses').select(
        'amount'
    ).gte(
        'expense_date', start_date.isoformat()
    ).lte(
        'expense_date', end_date.isoformat()
    ).execute()

    total_expenses = sum(
        e.get('amount', 0) or 0 for e in expenses_result.data
    )

    devotees_result = db.table('devotees').select(
        'id', count='exact'
    ).eq('is_active', True).eq('is_family_head', True).execute()
    total_devotees = devotees_result.count or 0

    # Display stat cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
            <div class="stat-card income">
                <h6>📈 {period.title()} Income</h6>
                <h3>{format_currency(total_income)}</h3>
            </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
            <div class="stat-card expense">
                <h6>📉 {period.title()} Expenses</h6>
                <h3>{format_currency(total_expenses)}</h3>
            </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
            <div class="stat-card devotees">
                <h6>👥 Total Devotees</h6>
                <h3>{total_devotees}</h3>
            </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
            <div class="stat-card bills">
                <h6>🧾 {period.title()} Bills</h6>
                <h3>{total_bills}</h3>
            </div>
        """, unsafe_allow_html=True)

    # Two columns - Pooja Schedule & Birthdays
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("### 🙏 Today's Pooja Schedule")
        poojas = db.table('daily_poojas').select('*').eq(
            'is_active', True
        ).execute()
        if poojas.data:
            for p in poojas.data:
                st.markdown(f"""
                    <div class="pooja-card">
                        <strong>{p['pooja_name']}</strong>
                        <span style="float:right; color:#8B0000; font-weight:700;">
                            {p.get('pooja_time', 'TBD')}
                        </span>
                        <br><small style="color:#666;">
                            {p.get('description', '')}
                        </small>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No pooja scheduled")

    with col_right:
        st.markdown("### 🎂 Today's Birthdays")
        all_devotees = db.table('devotees').select(
            'name, dob, mobile_no'
        ).eq('is_active', True).execute()

        birthday_list = []
        for d in all_devotees.data:
            if d.get('dob'):
                try:
                    dob = datetime.strptime(
                        d['dob'], '%Y-%m-%d'
                    ).date()
                    if (dob.month == today.month
                            and dob.day == today.day):
                        birthday_list.append(d)
                except (ValueError, TypeError):
                    pass

        if birthday_list:
            for b in birthday_list:
                st.markdown(f"""
                    <div class="birthday-card">
                        🎂 <strong>{b['name']}</strong>
                        <br><small>📱 {b.get('mobile_no', '-')}</small>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No birthdays today")

    # Recent Bills
    st.markdown("### 🧾 Recent Bills")
    recent = db.table('bills').select(
        '*, devotees(name), pooja_types(name)'
    ).eq('is_deleted', False).order(
        'created_at', desc=True
    ).limit(10).execute()

    if recent.data:
        bill_data = []
        for b in recent.data:
            name = ""
            if b.get('devotees'):
                name = b['devotees'].get('name', '')
            elif b.get('guest_name'):
                name = b['guest_name']
            pooja = ""
            if b.get('pooja_types'):
                pooja = b['pooja_types'].get('name', '')

            bill_data.append({
                'Bill No': b.get('bill_number', ''),
                'Date': b.get('bill_date', '')[:10] if b.get('bill_date') else '',
                'Name': name,
                'Pooja': pooja,
                'Amount': format_currency(b.get('amount', 0))
            })
        st.dataframe(
            pd.DataFrame(bill_data),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No bills yet")


# ============================================================
# DEVOTEES PAGE
# ============================================================
def devotees_page():
    """Devotees management page"""
    db = get_db()

    st.markdown(f"""
        <div class="main-header">
            <h1>👥 Devotee Management</h1>
        </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs([
        "📋 All Devotees",
        "➕ Add Devotee",
        "🔍 Search"
    ])

    with tab1:
        devotees = db.table('devotees').select('*').eq(
            'is_active', True
        ).eq('is_family_head', True).order(
            'name'
        ).execute()

        if devotees.data:
            for d in devotees.data:
                with st.expander(
                    f"👤 {d['name']} | 📱 {d.get('mobile_no', '-')} "
                    f"| ⭐ {d.get('natchathiram', '-')}"
                ):
                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        st.write(f"**Name:** {d['name']}")
                        st.write(f"**DOB:** {d.get('dob', '-')}")
                        st.write(f"**Mobile:** {d.get('mobile_no', '-')}")
                        st.write(f"**WhatsApp:** {d.get('whatsapp_no', '-')}")
                    with col2:
                        st.write(
                            f"**Natchathiram:** "
                            f"{d.get('natchathiram', '-')}"
                        )
                        st.write(
                            f"**Relation:** "
                            f"{d.get('relation_type', '-')}"
                        )
                        st.write(
                            f"**Wedding Day:** "
                            f"{d.get('wedding_day', '-')}"
                        )
                        st.write(f"**Address:** {d.get('address', '-')}")
                    with col3:
                        if d.get('photo_url'):
                            st.image(d['photo_url'], width=100)

                        if st.button(
                            "✏️ Edit",
                            key=f"edit_dev_{d['id']}"
                        ):
                            st.session_state['edit_devotee_id'] = d['id']
                            st.session_state['current_page'] = 'edit_devotee'
                            st.rerun()

                        if st.button(
                            "🗑️ Delete",
                            key=f"del_dev_{d['id']}"
                        ):
                            db.table('devotees').update(
                                {'is_active': False}
                            ).eq('id', d['id']).execute()
                            st.success("Deleted!")
                            time.sleep(0.5)
                            st.rerun()

                    # Family Members
                    family = db.table('devotees').select('*').eq(
                        'family_head_id', d['id']
                    ).eq('is_active', True).execute()

                    if family.data:
                        st.markdown("**👨‍👩‍👧‍👦 Family Members:**")
                        for fm in family.data:
                            st.write(
                                f"  - {fm['name']} "
                                f"({fm.get('relation_type', '-')}) "
                                f"| DOB: {fm.get('dob', '-')}"
                            )

                    # Yearly Poojas
                    yearly = db.table('devotee_yearly_poojas').select(
                        '*, pooja_types(name)'
                    ).eq('devotee_id', d['id']).execute()

                    if yearly.data:
                        st.markdown("**🙏 Yearly Poojas:**")
                        for yp in yearly.data:
                            pooja_name = ""
                            if yp.get('pooja_types'):
                                pooja_name = yp['pooja_types'].get(
                                    'name', ''
                                )
                            st.write(
                                f"  - {pooja_name} | "
                                f"Date: {yp.get('pooja_date', '-')} | "
                                f"Notes: {yp.get('notes', '-')}"
                            )
        else:
            st.info("No devotees found. Add your first devotee!")

    with tab2:
        add_devotee_form(db)

    with tab3:
        search = st.text_input("🔍 Search by Name or Mobile")
        if search:
            results = db.table('devotees').select('*').eq(
                'is_active', True
            ).or_(
                f"name.ilike.%{search}%,"
                f"mobile_no.ilike.%{search}%"
            ).execute()

            if results.data:
                for d in results.data:
                    st.write(
                        f"👤 **{d['name']}** | "
                        f"📱 {d.get('mobile_no', '-')} | "
                        f"⭐ {d.get('natchathiram', '-')}"
                    )
            else:
                st.warning("No results found")


def add_devotee_form(db):
    """Add devotee form"""
    with st.form("add_devotee_form"):
        st.markdown("#### 👤 Devotee Details")
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Name *")
            dob = st.date_input(
                "Date of Birth",
                value=None,
                min_value=date(1920, 1, 1),
                max_value=date.today()
            )
            mobile = st.text_input("Mobile Number")
            whatsapp = st.text_input("WhatsApp Number")

        with col2:
            relation = st.selectbox(
                "Relation Type",
                [''] + RELATION_TYPES
            )
            natchathiram = st.selectbox(
                "Natchathiram",
                [''] + NATCHATHIRAM_LIST
            )
            wedding = st.date_input(
                "Wedding Day",
                value=None,
                min_value=date(1950, 1, 1)
            )
            photo = st.file_uploader(
                "Photo",
                type=['jpg', 'jpeg', 'png']
            )

        address = st.text_area("Address")

        # Family Members
        st.markdown("---")
        st.markdown("#### 👨‍👩‍👧‍👦 Family Members")
        num_family = st.number_input(
            "Number of family members to add",
            0, 20, 0
        )

        family_data = []
        for i in range(int(num_family)):
            st.markdown(f"**Family Member {i+1}**")
            fc1, fc2, fc3 = st.columns(3)
            with fc1:
                fm_name = st.text_input(
                    f"Name",
                    key=f"fm_name_{i}"
                )
            with fc2:
                fm_dob = st.date_input(
                    f"DOB",
                    value=None,
                    key=f"fm_dob_{i}",
                    min_value=date(1920, 1, 1)
                )
            with fc3:
                fm_rel = st.selectbox(
                    f"Relation",
                    [''] + RELATION_TYPES,
                    key=f"fm_rel_{i}"
                )
            family_data.append({
                'name': fm_name,
                'dob': fm_dob,
                'relation': fm_rel
            })

        # Yearly Poojas
        st.markdown("---")
        st.markdown("#### 🙏 Yearly Poojas")
        pooja_types_result = db.table('pooja_types').select('*').eq(
            'is_active', True
        ).execute()
        pooja_types = pooja_types_result.data

        num_poojas = st.number_input(
            "Number of yearly poojas to add",
            0, 20, 0
        )
        pooja_data = []
        for i in range(int(num_poojas)):
            pc1, pc2, pc3 = st.columns(3)
            with pc1:
                pt_sel = st.selectbox(
                    f"Pooja Type",
                    [''] + [p['name'] for p in pooja_types],
                    key=f"yp_type_{i}"
                )
            with pc2:
                yp_date = st.date_input(
                    f"Pooja Date",
                    value=None,
                    key=f"yp_date_{i}"
                )
            with pc3:
                yp_notes = st.text_input(
                    f"Notes",
                    key=f"yp_notes_{i}"
                )

            pt_id = None
            for p in pooja_types:
                if p['name'] == pt_sel:
                    pt_id = p['id']
                    break

            pooja_data.append({
                'pooja_type_id': pt_id,
                'pooja_name': pt_sel,
                'pooja_date': yp_date,
                'notes': yp_notes
            })

        submitted = st.form_submit_button(
            "💾 Save Devotee",
            use_container_width=True
        )

        if submitted:
            if not name:
                st.error("Name is required!")
                return

            # Upload photo
            photo_url = None
            if photo:
                filename = f"devotee_{datetime.now().strftime('%Y%m%d%H%M%S')}_{photo.name}"
                photo_url = upload_to_supabase_storage(
                    photo, 'devotees', filename
                )

            # Insert devotee
            devotee_data = {
                'name': name,
                'dob': dob.isoformat() if dob else None,
                'relation_type': relation if relation else None,
                'mobile_no': mobile if mobile else None,
                'whatsapp_no': whatsapp if whatsapp else None,
                'wedding_day': wedding.isoformat() if wedding else None,
                'natchathiram': (
                    natchathiram if natchathiram else None
                ),
                'address': address if address else None,
                'photo_url': photo_url,
                'is_family_head': True,
                'is_active': True
            }

            result = db.table('devotees').insert(
                devotee_data
            ).execute()
            devotee_id = result.data[0]['id']

            # Insert family members
            for fm in family_data:
                if fm['name']:
                    db.table('devotees').insert({
                        'name': fm['name'],
                        'dob': (
                            fm['dob'].isoformat()
                            if fm['dob'] else None
                        ),
                        'relation_type': (
                            fm['relation'] if fm['relation'] else None
                        ),
                        'is_family_head': False,
                        'family_head_id': devotee_id,
                        'is_active': True
                    }).execute()

            # Insert yearly poojas
            for yp in pooja_data:
                if yp['pooja_type_id'] or yp['pooja_name']:
                    db.table('devotee_yearly_poojas').insert({
                        'devotee_id': devotee_id,
                        'pooja_type_id': yp['pooja_type_id'],
                        'pooja_name': yp['pooja_name'],
                        'pooja_date': (
                            yp['pooja_date'].isoformat()
                            if yp['pooja_date'] else None
                        ),
                        'notes': yp['notes'] if yp['notes'] else None
                    }).execute()

            st.success("✅ Devotee added successfully!")
            time.sleep(1)
            st.rerun()


# ============================================================
# BILLING PAGE
# ============================================================
def billing_page():
    """Billing management"""
    db = get_db()

    st.markdown("""
        <div class="main-header">
            <h1>🧾 Billing</h1>
        </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📋 Bills List", "➕ New Bill"])

    with tab1:
        # Date filter
        col1, col2 = st.columns(2)
        with col1:
            from_date = st.date_input(
                "From Date",
                value=date.today()
            )
        with col2:
            to_date = st.date_input(
                "To Date",
                value=date.today()
            )

        bills = db.table('bills').select(
            '*, devotees(name), pooja_types(name)'
        ).eq('is_deleted', False).gte(
            'bill_date', from_date.isoformat()
        ).lte(
            'bill_date', to_date.isoformat() + "T23:59:59"
        ).order('created_at', desc=True).execute()

        if bills.data:
            total = sum(b.get('amount', 0) or 0 for b in bills.data)
            st.markdown(
                f"**Total: {format_currency(total)} "
                f"| Bills: {len(bills.data)}**"
            )

            for b in bills.data:
                name = ""
                if b.get('devotees'):
                    name = b['devotees'].get('name', '')
                elif b.get('guest_name'):
                    name = b['guest_name']

                pooja = ""
                if b.get('pooja_types'):
                    pooja = b['pooja_types'].get('name', '')

                with st.expander(
                    f"🧾 {b.get('bill_number', '')} | "
                    f"{name} | {pooja} | "
                    f"{format_currency(b.get('amount', 0))}"
                ):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.write(
                            f"**Bill No:** {b.get('bill_number', '')}"
                        )
                        st.write(
                            f"**Manual Bill:** "
                            f"{b.get('manual_bill_no', '-')}"
                        )
                        st.write(
                            f"**Bill Book:** "
                            f"{b.get('bill_book_no', '-')}"
                        )
                    with c2:
                        st.write(f"**Name:** {name}")
                        st.write(f"**Pooja:** {pooja}")
                        st.write(
                            f"**Amount:** "
                            f"{format_currency(b.get('amount', 0))}"
                        )
                    with c3:
                        st.write(
                            f"**Date:** "
                            f"{b.get('bill_date', '')[:10]}"
                        )
                        st.write(
                            f"**Notes:** {b.get('notes', '-')}"
                        )

                        # Print bill button
                        if st.button(
                            "🖨️ Print",
                            key=f"print_{b['id']}"
                        ):
                            show_bill_print(b, name, pooja)

                        # Delete bill (admin only)
                        if st.session_state['role'] == 'admin':
                            reason = st.text_input(
                                "Delete reason",
                                key=f"del_reason_{b['id']}"
                            )
                            if st.button(
                                "🗑️ Delete",
                                key=f"del_bill_{b['id']}"
                            ):
                                if reason:
                                    db.table('bills').update({
                                        'is_deleted': True,
                                        'deleted_by': (
                                            st.session_state['user_id']
                                        ),
                                        'deleted_at': (
                                            datetime.now().isoformat()
                                        ),
                                        'delete_reason': reason
                                    }).eq('id', b['id']).execute()
                                    st.success("Bill deleted!")
                                    time.sleep(0.5)
                                    st.rerun()
                                else:
                                    st.warning(
                                        "Please provide delete reason"
                                    )
        else:
            st.info("No bills for selected period")

    with tab2:
        new_bill_form(db)


def new_bill_form(db):
    """New bill creation form"""
    pooja_types = db.table('pooja_types').select('*').eq(
        'is_active', True
    ).execute().data

    with st.form("new_bill_form"):
        st.markdown("#### 🧾 New Bill")

        col1, col2 = st.columns(2)
        with col1:
            manual_bill = st.text_input("Manual Bill No")
            bill_book = st.text_input("Bill Book No")
            bill_date = st.date_input("Bill Date", value=date.today())

        with col2:
            devotee_type = st.radio(
                "Devotee Type",
                ['Enrolled', 'Guest'],
                horizontal=True
            )

        if devotee_type == 'Enrolled':
            devotees = db.table('devotees').select(
                'id, name, mobile_no'
            ).eq('is_active', True).eq(
                'is_family_head', True
            ).order('name').execute()

            devotee_options = {
                f"{d['name']} ({d.get('mobile_no', '-')})": d['id']
                for d in devotees.data
            }
            selected = st.selectbox(
                "Select Devotee",
                [''] + list(devotee_options.keys())
            )
            devotee_id = (
                devotee_options.get(selected) if selected else None
            )
            guest_name = None
            guest_address = None
            guest_mobile = None
            guest_whatsapp = None
        else:
            devotee_id = None
            guest_name = st.text_input("Guest Name *")
            guest_address = st.text_area("Guest Address")
            gc1, gc2 = st.columns(2)
            with gc1:
                guest_mobile = st.text_input("Guest Mobile")
            with gc2:
                guest_whatsapp = st.text_input("Guest WhatsApp")

        pooja_options = {p['name']: p for p in pooja_types}
        selected_pooja = st.selectbox(
            "Pooja Type *",
            [''] + list(pooja_options.keys())
        )

        amount = 0.0
        if selected_pooja and selected_pooja in pooja_options:
            amount = pooja_options[selected_pooja].get('amount', 0)

        amount = st.number_input(
            "Amount (₹)",
            value=float(amount),
            min_value=0.0,
            step=10.0
        )
        notes = st.text_area("Notes")

        submitted = st.form_submit_button(
            "💾 Create Bill",
            use_container_width=True
        )

        if submitted:
            if devotee_type == 'Enrolled' and not devotee_id:
                st.error("Please select a devotee!")
                return
            if devotee_type == 'Guest' and not guest_name:
                st.error("Please enter guest name!")
                return
            if not selected_pooja:
                st.error("Please select pooja type!")
                return

            bill_number = generate_bill_number()
            pooja_type_id = None
            if selected_pooja in pooja_options:
                pooja_type_id = pooja_options[selected_pooja]['id']

            bill_data = {
                'bill_number': bill_number,
                'manual_bill_no': (
                    manual_bill if manual_bill else None
                ),
                'bill_book_no': bill_book if bill_book else None,
                'bill_date': (
                    datetime.combine(
                        bill_date, datetime.now().time()
                    ).isoformat()
                ),
                'devotee_type': devotee_type.lower(),
                'devotee_id': devotee_id,
                'guest_name': guest_name,
                'guest_address': guest_address,
                'guest_mobile': guest_mobile,
                'guest_whatsapp': guest_whatsapp,
                'pooja_type_id': pooja_type_id,
                'amount': amount,
                'notes': notes if notes else None,
                'is_deleted': False,
                'created_by': st.session_state['user_id']
            }

            db.table('bills').insert(bill_data).execute()
            st.success(f"✅ Bill {bill_number} created successfully!")
            st.balloons()
            time.sleep(1)
            st.rerun()


def show_bill_print(bill, name, pooja):
    """Show printable bill"""
    st.markdown(f"""
    <div style="border:2px solid #8B0000; padding:20px; border-radius:10px;
                max-width:500px; margin:10px auto; background:white;">
        <div class="bill-header">
            <h3>🕉️ {TEMPLE_NAME}</h3>
            <h5>{TEMPLE_ADDRESS_LINE2}</h5>
            <p>{TEMPLE_ADDRESS_LINE3}</p>
        </div>
        <div style="text-align:center; margin-bottom:15px;">
            <h4 style="color:#8B0000;">RECEIPT / பற்றுச்சீட்டு</h4>
        </div>
        <table style="width:100%; border-collapse:collapse;">
            <tr>
                <td style="padding:5px;"><strong>Bill No:</strong></td>
                <td style="padding:5px;">{bill.get('bill_number', '')}</td>
                <td style="padding:5px;"><strong>Date:</strong></td>
                <td style="padding:5px;">
                    {bill.get('bill_date', '')[:10]}
                </td>
            </tr>
            <tr>
                <td style="padding:5px;"><strong>Name:</strong></td>
                <td colspan="3" style="padding:5px;">{name}</td>
            </tr>
            <tr>
                <td style="padding:5px;"><strong>Pooja:</strong></td>
                <td colspan="3" style="padding:5px;">{pooja}</td>
            </tr>
            <tr style="background:#FFF8DC;">
                <td style="padding:8px;"><strong>Amount:</strong></td>
                <td colspan="3" style="padding:8px; font-size:1.3em;
                    color:#8B0000; font-weight:700;">
                    {format_currency(bill.get('amount', 0))}
                </td>
            </tr>
        </table>
        <div style="text-align:center; margin-top:15px;
                    border-top:1px dashed #ccc; padding-top:10px;">
            <small style="color:#666;">
                🙏 Thank you for your offering 🙏
            </small>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# EXPENSES PAGE
# ============================================================
def expenses_page():
    """Expense management"""
    db = get_db()

    st.markdown("""
        <div class="main-header">
            <h1>💰 Expense Management</h1>
        </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📋 Expenses List", "➕ Add Expense"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            from_date = st.date_input(
                "From",
                value=date.today().replace(day=1),
                key="exp_from"
            )
        with col2:
            to_date = st.date_input(
                "To",
                value=date.today(),
                key="exp_to"
            )

        expenses = db.table('expenses').select(
            '*, expense_types(name)'
        ).gte(
            'expense_date', from_date.isoformat()
        ).lte(
            'expense_date', to_date.isoformat()
        ).order('expense_date', desc=True).execute()

        if expenses.data:
            total = sum(
                e.get('amount', 0) or 0 for e in expenses.data
            )
            st.markdown(
                f"**Total Expenses: {format_currency(total)}**"
            )

            exp_data = []
            for e in expenses.data:
                exp_type = ""
                if e.get('expense_types'):
                    exp_type = e['expense_types'].get('name', '')
                exp_data.append({
                    'Date': e.get('expense_date', ''),
                    'Type': exp_type,
                    'Description': e.get('description', ''),
                    'Amount': format_currency(e.get('amount', 0))
                })
            st.dataframe(
                pd.DataFrame(exp_data),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No expenses for selected period")

    with tab2:
        expense_types = db.table('expense_types').select('*').eq(
            'is_active', True
        ).execute().data

        with st.form("add_expense"):
            col1, col2 = st.columns(2)
            with col1:
                exp_type_options = {
                    e['name']: e['id'] for e in expense_types
                }
                selected_type = st.selectbox(
                    "Expense Type *",
                    [''] + list(exp_type_options.keys())
                )
                amount = st.number_input(
                    "Amount (₹) *",
                    min_value=0.0,
                    step=10.0
                )
            with col2:
                exp_date = st.date_input(
                    "Date",
                    value=date.today()
                )
                description = st.text_area("Description")

            submitted = st.form_submit_button(
                "💾 Add Expense",
                use_container_width=True
            )

            if submitted:
                if not selected_type or amount <= 0:
                    st.error(
                        "Please select type and enter valid amount!"
                    )
                else:
                    db.table('expenses').insert({
                        'expense_type_id': (
                            exp_type_options[selected_type]
                        ),
                        'amount': amount,
                        'description': (
                            description if description else None
                        ),
                        'expense_date': exp_date.isoformat(),
                        'created_by': st.session_state['user_id']
                    }).execute()
                    st.success("✅ Expense added!")
                    time.sleep(0.5)
                    st.rerun()


# ============================================================
# REPORTS PAGE
# ============================================================
def reports_page():
    """Reports and analytics"""
    db = get_db()

    st.markdown("""
        <div class="main-header">
            <h1>📈 Reports & Analytics</h1>
        </div>
    """, unsafe_allow_html=True)

    report_type = st.selectbox(
        "Select Report",
        [
            "Income Summary",
            "Expense Summary",
            "Income vs Expense",
            "Pooja-wise Income",
            "Monthly Trend"
        ]
    )

    col1, col2 = st.columns(2)
    with col1:
        from_date = st.date_input(
            "From",
            value=date.today().replace(month=1, day=1),
            key="rep_from"
        )
    with col2:
        to_date = st.date_input(
            "To",
            value=date.today(),
            key="rep_to"
        )

    if report_type == "Income Summary":
        bills = db.table('bills').select(
            'amount, bill_date'
        ).eq('is_deleted', False).gte(
            'bill_date', from_date.isoformat()
        ).lte(
            'bill_date', to_date.isoformat() + "T23:59:59"
        ).execute()

        if bills.data:
            df = pd.DataFrame(bills.data)
            df['bill_date'] = pd.to_datetime(df['bill_date'])
            df['date'] = df['bill_date'].dt.date

            daily = df.groupby('date')['amount'].sum().reset_index()
            fig = px.bar(
                daily, x='date', y='amount',
                title="Daily Income",
                color_discrete_sequence=['#228B22']
            )
            st.plotly_chart(fig, use_container_width=True)

            total = df['amount'].sum()
            st.metric("Total Income", format_currency(total))
        else:
            st.info("No data for selected period")

    elif report_type == "Expense Summary":
        expenses = db.table('expenses').select(
            '*, expense_types(name)'
        ).gte(
            'expense_date', from_date.isoformat()
        ).lte(
            'expense_date', to_date.isoformat()
        ).execute()

        if expenses.data:
            data = []
            for e in expenses.data:
                etype = ""
                if e.get('expense_types'):
                    etype = e['expense_types'].get('name', '')
                data.append({
                    'type': etype,
                    'amount': e.get('amount', 0)
                })
            df = pd.DataFrame(data)
            type_sum = df.groupby('type')['amount'].sum().reset_index()

            fig = px.pie(
                type_sum, values='amount', names='type',
                title="Expense Breakdown",
                color_discrete_sequence=px.colors.sequential.Reds
            )
            st.plotly_chart(fig, use_container_width=True)

            total = df['amount'].sum()
            st.metric("Total Expenses", format_currency(total))
        else:
            st.info("No data for selected period")

    elif report_type == "Income vs Expense":
        bills = db.table('bills').select('amount').eq(
            'is_deleted', False
        ).gte(
            'bill_date', from_date.isoformat()
        ).lte(
            'bill_date', to_date.isoformat() + "T23:59:59"
        ).execute()

        expenses = db.table('expenses').select('amount').gte(
            'expense_date', from_date.isoformat()
        ).lte(
            'expense_date', to_date.isoformat()
        ).execute()

        income_total = sum(
            b.get('amount', 0) or 0 for b in bills.data
        )
        expense_total = sum(
            e.get('amount', 0) or 0 for e in expenses.data
        )

        fig = go.Figure(data=[
            go.Bar(
                name='Income',
                x=['Income'],
                y=[income_total],
                marker_color='#228B22'
            ),
            go.Bar(
                name='Expense',
                x=['Expense'],
                y=[expense_total],
                marker_color='#DC143C'
            )
        ])
        fig.update_layout(title="Income vs Expense")
        st.plotly_chart(fig, use_container_width=True)

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Income", format_currency(income_total))
        with c2:
            st.metric("Expenses", format_currency(expense_total))
        with c3:
            st.metric(
                "Net",
                format_currency(income_total - expense_total)
            )

    elif report_type == "Pooja-wise Income":
        bills = db.table('bills').select(
            'amount, pooja_types(name)'
        ).eq('is_deleted', False).gte(
            'bill_date', from_date.isoformat()
        ).lte(
            'bill_date', to_date.isoformat() + "T23:59:59"
        ).execute()

        if bills.data:
            data = []
            for b in bills.data:
                pname = ""
                if b.get('pooja_types'):
                    pname = b['pooja_types'].get('name', '')
                data.append({
                    'pooja': pname,
                    'amount': b.get('amount', 0)
                })
            df = pd.DataFrame(data)
            pooja_sum = df.groupby(
                'pooja'
            )['amount'].sum().reset_index()

            fig = px.bar(
                pooja_sum, x='pooja', y='amount',
                title="Income by Pooja Type",
                color_discrete_sequence=['#8B0000']
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data for selected period")

    elif report_type == "Monthly Trend":
        bills = db.table('bills').select(
            'amount, bill_date'
        ).eq('is_deleted', False).gte(
            'bill_date', from_date.isoformat()
        ).lte(
            'bill_date', to_date.isoformat() + "T23:59:59"
        ).execute()

        if bills.data:
            df = pd.DataFrame(bills.data)
            df['bill_date'] = pd.to_datetime(df['bill_date'])
            df['month'] = df['bill_date'].dt.to_period('M').astype(str)
            monthly = df.groupby(
                'month'
            )['amount'].sum().reset_index()

            fig = px.line(
                monthly, x='month', y='amount',
                title="Monthly Income Trend",
                markers=True,
                color_discrete_sequence=['#8B0000']
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data for selected period")


# ============================================================
# SAMAYA VAKUPPU PAGE
# ============================================================
def samaya_vakuppu_page():
    """Samaya Vakuppu management"""
    db = get_db()

    st.markdown("""
        <div class="main-header">
            <h1>🎓 Samaya Vakuppu</h1>
        </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📋 Students", "➕ Add Student"])

    with tab1:
        students = db.table('samaya_vakuppu').select('*').order(
            'student_name'
        ).execute()

        if students.data:
            for s in students.data:
                with st.expander(
                    f"🎓 {s['student_name']} | "
                    f"Bond: {s.get('bond_no', '-')}"
                ):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write(
                            f"**Name:** {s['student_name']}"
                        )
                        st.write(f"**DOB:** {s.get('dob', '-')}")
                        st.write(
                            f"**Parent:** "
                            f"{s.get('father_mother_name', '-')}"
                        )
                        st.write(
                            f"**Address:** {s.get('address', '-')}"
                        )
                    with c2:
                        st.write(
                            f"**Bond No:** {s.get('bond_no', '-')}"
                        )
                        st.write(
                            f"**Bond Date:** "
                            f"{s.get('bond_issue_date', '-')}"
                        )
                        st.write(
                            f"**Bank:** "
                            f"{s.get('bond_issuing_bank', '-')}"
                        )
                        st.write(
                            f"**Branch:** "
                            f"{s.get('branch_of_bank', '-')}"
                        )

                    if st.button(
                        "🗑️ Delete",
                        key=f"del_sam_{s['id']}"
                    ):
                        db.table('samaya_vakuppu').delete().eq(
                            'id', s['id']
                        ).execute()
                        st.success("Deleted!")
                        time.sleep(0.5)
                        st.rerun()
        else:
            st.info("No students registered")

    with tab2:
        with st.form("add_samaya"):
            c1, c2 = st.columns(2)
            with c1:
                s_name = st.text_input("Student Name *")
                s_dob = st.date_input(
                    "DOB",
                    value=None,
                    min_value=date(1950, 1, 1),
                    key="sam_dob"
                )
                parent = st.text_input("Father/Mother Name")
                address = st.text_area("Address")
            with c2:
                bond_no = st.text_input("Bond No")
                bond_date = st.date_input(
                    "Bond Issue Date",
                    value=None,
                    key="sam_bond_date"
                )
                bank = st.text_input("Bond Issuing Bank")
                branch = st.text_input("Branch of Bank")

            photo = st.file_uploader(
                "Photo",
                type=['jpg', 'jpeg', 'png'],
                key="sam_photo"
            )
            bond_scan = st.file_uploader(
                "Bond Scan",
                type=['jpg', 'jpeg', 'png', 'pdf'],
                key="sam_bond"
            )

            if st.form_submit_button(
                "💾 Save",
                use_container_width=True
            ):
                if not s_name:
                    st.error("Student name is required!")
                else:
                    photo_url = None
                    bond_url = None

                    if photo:
                        fn = (
                            f"samaya_photo_"
                            f"{datetime.now().strftime('%Y%m%d%H%M%S')}"
                            f"_{photo.name}"
                        )
                        photo_url = upload_to_supabase_storage(
                            photo, 'samaya', fn
                        )
                    if bond_scan:
                        fn = (
                            f"samaya_bond_"
                            f"{datetime.now().strftime('%Y%m%d%H%M%S')}"
                            f"_{bond_scan.name}"
                        )
                        bond_url = upload_to_supabase_storage(
                            bond_scan, 'samaya', fn
                        )

                    db.table('samaya_vakuppu').insert({
                        'student_name': s_name,
                        'dob': (
                            s_dob.isoformat() if s_dob else None
                        ),
                        'father_mother_name': (
                            parent if parent else None
                        ),
                        'address': address if address else None,
                        'bond_no': bond_no if bond_no else None,
                        'bond_issue_date': (
                            bond_date.isoformat()
                            if bond_date else None
                        ),
                        'bond_issuing_bank': (
                            bank if bank else None
                        ),
                        'branch_of_bank': (
                            branch if branch else None
                        ),
                        'photo_url': photo_url,
                        'bond_scan_url': bond_url
                    }).execute()
                    st.success("✅ Student added!")
                    time.sleep(0.5)
                    st.rerun()


# ============================================================
# THIRUMANA MANDAPAM PAGE
# ============================================================
def thirumana_mandapam_page():
    """Thirumana Mandapam management"""
    db = get_db()

    st.markdown("""
        <div class="main-header">
            <h1>🏛️ Thirumana Mandapam</h1>
        </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📋 Records", "➕ Add Record"])

    with tab1:
        records = db.table('thirumana_mandapam').select('*').order(
            'name'
        ).execute()

        if records.data:
            for r in records.data:
                with st.expander(
                    f"🏛️ {r['name']} | "
                    f"Bond: {r.get('bond_no', '-')} | "
                    f"{format_currency(r.get('amount', 0))}"
                ):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write(f"**Name:** {r['name']}")
                        st.write(
                            f"**Address:** {r.get('address', '-')}"
                        )
                        st.write(
                            f"**Bond No:** {r.get('bond_no', '-')}"
                        )
                    with c2:
                        st.write(
                            f"**Bond Date:** "
                            f"{r.get('bond_issued_date', '-')}"
                        )
                        st.write(
                            f"**Amount:** "
                            f"{format_currency(r.get('amount', 0))}"
                        )
                        st.write(
                            f"**No of Bonds:** "
                            f"{r.get('no_of_bond', 1)}"
                        )

                    if st.button(
                        "🗑️ Delete",
                        key=f"del_mand_{r['id']}"
                    ):
                        db.table('thirumana_mandapam').delete().eq(
                            'id', r['id']
                        ).execute()
                        st.success("Deleted!")
                        time.sleep(0.5)
                        st.rerun()
        else:
            st.info("No records found")

    with tab2:
        with st.form("add_mandapam"):
            c1, c2 = st.columns(2)
            with c1:
                m_name = st.text_input("Name *")
                m_address = st.text_area("Address")
                m_bond = st.text_input("Bond No")
            with c2:
                m_date = st.date_input(
                    "Bond Issued Date",
                    value=None,
                    key="mand_date"
                )
                m_amount = st.number_input(
                    "Amount",
                    min_value=0.0,
                    step=100.0
                )
                m_count = st.number_input(
                    "No of Bonds",
                    min_value=1,
                    value=1
                )

            m_photo = st.file_uploader(
                "Photo",
                type=['jpg', 'jpeg', 'png'],
                key="mand_photo"
            )
            m_bond_scan = st.file_uploader(
                "Bond Scan",
                type=['jpg', 'jpeg', 'png', 'pdf'],
                key="mand_bond"
            )

            if st.form_submit_button(
                "💾 Save",
                use_container_width=True
            ):
                if not m_name:
                    st.error("Name is required!")
                else:
                    photo_url = None
                    bond_url = None
                    if m_photo:
                        fn = (
                            f"mand_photo_"
                            f"{datetime.now().strftime('%Y%m%d%H%M%S')}"
                            f"_{m_photo.name}"
                        )
                        photo_url = upload_to_supabase_storage(
                            m_photo, 'mandapam', fn
                        )
                    if m_bond_scan:
                        fn = (
                            f"mand_bond_"
                            f"{datetime.now().strftime('%Y%m%d%H%M%S')}"
                            f"_{m_bond_scan.name}"
                        )
                        bond_url = upload_to_supabase_storage(
                            m_bond_scan, 'mandapam', fn
                        )

                    db.table('thirumana_mandapam').insert({
                        'name': m_name,
                        'address': (
                            m_address if m_address else None
                        ),
                        'bond_no': m_bond if m_bond else None,
                        'bond_issued_date': (
                            m_date.isoformat()
                            if m_date else None
                        ),
                        'amount': m_amount,
                        'no_of_bond': m_count,
                        'photo_url': photo_url,
                        'bond_scan_url': bond_url
                    }).execute()
                    st.success("✅ Record added!")
                    time.sleep(0.5)
                    st.rerun()


# ============================================================
# DAILY POOJA PAGE
# ============================================================
def daily_pooja_page():
    """Daily Pooja management"""
    db = get_db()

    st.markdown("""
        <div class="main-header">
            <h1>🙏 Daily Pooja Schedule</h1>
        </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📋 Schedule", "➕ Add Pooja"])

    with tab1:
        poojas = db.table('daily_poojas').select('*').order(
            'pooja_time'
        ).execute()

        if poojas.data:
            for p in poojas.data:
                status = "🟢" if p.get('is_active') else "🔴"
                st.markdown(f"""
                    <div class="pooja-card">
                        <strong>{status} {p['pooja_name']}</strong>
                        <span style="float:right; color:#8B0000;
                            font-weight:700;">
                            {p.get('pooja_time', 'TBD')}
                        </span>
                        <br><small style="color:#666;">
                            {p.get('description', '')}
                        </small>
                    </div>
                """, unsafe_allow_html=True)

                c1, c2 = st.columns([1, 1])
                with c1:
                    if st.button(
                        "🔄 Toggle",
                        key=f"toggle_pooja_{p['id']}"
                    ):
                        db.table('daily_poojas').update({
                            'is_active': not p.get('is_active', True)
                        }).eq('id', p['id']).execute()
                        st.rerun()
                with c2:
                    if st.button(
                        "🗑️ Delete",
                        key=f"del_pooja_{p['id']}"
                    ):
                        db.table('daily_poojas').delete().eq(
                            'id', p['id']
                        ).execute()
                        st.rerun()
        else:
            st.info("No poojas scheduled")

    with tab2:
        with st.form("add_daily_pooja"):
            p_name = st.text_input("Pooja Name *")
            p_time = st.text_input(
                "Time (e.g., 06:00 AM)"
            )
            p_desc = st.text_area("Description")

            if st.form_submit_button(
                "💾 Save",
                use_container_width=True
            ):
                if not p_name:
                    st.error("Pooja name is required!")
                else:
                    db.table('daily_poojas').insert({
                        'pooja_name': p_name,
                        'pooja_time': p_time if p_time else None,
                        'description': p_desc if p_desc else None,
                        'is_active': True
                    }).execute()
                    st.success("✅ Pooja added!")
                    time.sleep(0.5)
                    st.rerun()


# ============================================================
# SETTINGS PAGE
# ============================================================
def settings_page():
    """Settings management"""
    db = get_db()

    st.markdown("""
        <div class="main-header">
            <h1>⚙️ Settings</h1>
        </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs([
        "🙏 Pooja Types",
        "💰 Expense Types",
        "🔑 Change Password"
    ])

    with tab1:
        st.markdown("#### Pooja Types")
        pooja_types = db.table('pooja_types').select('*').order(
            'name'
        ).execute()

        if pooja_types.data:
            for pt in pooja_types.data:
                c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                with c1:
                    st.write(pt['name'])
                with c2:
                    st.write(format_currency(pt.get('amount', 0)))
                with c3:
                    status = "✅" if pt.get('is_active') else "❌"
                    st.write(status)
                with c4:
                    if st.button(
                        "🔄",
                        key=f"toggle_pt_{pt['id']}"
                    ):
                        db.table('pooja_types').update({
                            'is_active': not pt.get('is_active', True)
                        }).eq('id', pt['id']).execute()
                        st.rerun()

        st.markdown("---")
        st.markdown("**Add New Pooja Type**")
        with st.form("add_pooja_type"):
            c1, c2 = st.columns(2)
            with c1:
                pt_name = st.text_input("Pooja Name *")
            with c2:
                pt_amount = st.number_input(
                    "Amount",
                    min_value=0.0,
                    step=10.0
                )
            if st.form_submit_button("💾 Add"):
                if pt_name:
                    db.table('pooja_types').insert({
                        'name': pt_name,
                        'amount': pt_amount,
                        'is_active': True
                    }).execute()
                    st.success("✅ Added!")
                    time.sleep(0.5)
                    st.rerun()

    with tab2:
        st.markdown("#### Expense Types")
        exp_types = db.table('expense_types').select('*').order(
            'name'
        ).execute()

        if exp_types.data:
            for et in exp_types.data:
                c1, c2, c3 = st.columns([4, 1, 1])
                with c1:
                    st.write(et['name'])
                with c2:
                    status = "✅" if et.get('is_active') else "❌"
                    st.write(status)
                with c3:
                    if st.button(
                        "🔄",
                        key=f"toggle_et_{et['id']}"
                    ):
                        db.table('expense_types').update({
                            'is_active': not et.get('is_active', True)
                        }).eq('id', et['id']).execute()
                        st.rerun()

        st.markdown("---")
        st.markdown("**Add New Expense Type**")
        with st.form("add_expense_type"):
            et_name = st.text_input("Expense Type Name *")
            if st.form_submit_button("💾 Add"):
                if et_name:
                    db.table('expense_types').insert({
                        'name': et_name,
                        'is_active': True
                    }).execute()
                    st.success("✅ Added!")
                    time.sleep(0.5)
                    st.rerun()

    with tab3:
        st.markdown("#### Change Password")
        with st.form("change_password"):
            current_pw = st.text_input(
                "Current Password",
                type="password"
            )
            new_pw = st.text_input(
                "New Password",
                type="password"
            )
            confirm_pw = st.text_input(
                "Confirm New Password",
                type="password"
            )

            if st.form_submit_button("🔑 Change Password"):
                if not all([current_pw, new_pw, confirm_pw]):
                    st.error("All fields are required!")
                elif new_pw != confirm_pw:
                    st.error("New passwords don't match!")
                elif len(new_pw) < 6:
                    st.error("Password must be at least 6 characters!")
                else:
                    user = db.table('users').select('*').eq(
                        'id', st.session_state['user_id']
                    ).execute()
                    if user.data and check_password(
                        current_pw, user.data[0]['password_hash']
                    ):
                        db.table('users').update({
                            'password_hash': hash_password(new_pw)
                        }).eq(
                            'id', st.session_state['user_id']
                        ).execute()
                        st.success("✅ Password changed!")
                    else:
                        st.error("❌ Current password is incorrect!")


# ============================================================
# USER MANAGEMENT PAGE (Admin Only)
# ============================================================
def user_management_page():
    """User management - Admin only"""
    if st.session_state['role'] != 'admin':
        st.error("⛔ Admin access required!")
        return

    db = get_db()

    st.markdown("""
        <div class="main-header">
            <h1>👤 User Management</h1>
        </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📋 Users", "➕ Add User"])

    with tab1:
        users = db.table('users').select('*').order(
            'username'
        ).execute()

        if users.data:
            for u in users.data:
                c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 1, 1])
                with c1:
                    st.write(f"**{u['username']}**")
                with c2:
                    st.write(u.get('full_name', '-'))
                with c3:
                    st.write(u.get('role', 'user').upper())
                with c4:
                    status = (
                        "✅ Active"
                        if u.get('is_active_user', True)
                        else "❌ Inactive"
                    )
                    st.write(status)
                with c5:
                    if (u['username'] != 'admin'
                            and u['id'] != st.session_state['user_id']):
                        if st.button(
                            "🔄",
                            key=f"toggle_user_{u['id']}"
                        ):
                            db.table('users').update({
                                'is_active_user': not u.get(
                                    'is_active_user', True
                                )
                            }).eq('id', u['id']).execute()
                            st.rerun()

    with tab2:
        with st.form("add_user"):
            c1, c2 = st.columns(2)
            with c1:
                new_username = st.text_input("Username *")
                new_password = st.text_input(
                    "Password *",
                    type="password"
                )
            with c2:
                new_fullname = st.text_input("Full Name")
                new_role = st.selectbox(
                    "Role",
                    ['user', 'admin']
                )

            if st.form_submit_button(
                "💾 Create User",
                use_container_width=True
            ):
                if not new_username or not new_password:
                    st.error("Username and password are required!")
                elif len(new_password) < 6:
                    st.error(
                        "Password must be at least 6 characters!"
                    )
                else:
                    existing = db.table('users').select('id').eq(
                        'username', new_username
                    ).execute()
                    if existing.data:
                        st.error("Username already exists!")
                    else:
                        db.table('users').insert({
                            'username': new_username,
                            'password_hash': hash_password(
                                new_password
                            ),
                            'full_name': (
                                new_fullname
                                if new_fullname else None
                            ),
                            'role': new_role,
                            'is_active_user': True
                        }).execute()
                        st.success("✅ User created!")
                        time.sleep(0.5)
                        st.rerun()


# ============================================================
# DELETED BILLS PAGE (Admin Only)
# ============================================================
def deleted_bills_page():
    """View deleted bills - Admin only"""
    if st.session_state['role'] != 'admin':
        st.error("⛔ Admin access required!")
        return

    db = get_db()

    st.markdown("""
        <div class="main-header">
            <h1>🗑️ Deleted Bills</h1>
        </div>
    """, unsafe_allow_html=True)

    bills = db.table('bills').select(
        '*, devotees(name), pooja_types(name)'
    ).eq('is_deleted', True).order(
        'deleted_at', desc=True
    ).execute()

    if bills.data:
        for b in bills.data:
            name = ""
            if b.get('devotees'):
                name = b['devotees'].get('name', '')
            elif b.get('guest_name'):
                name = b['guest_name']

            pooja = ""
            if b.get('pooja_types'):
                pooja = b['pooja_types'].get('name', '')

            st.markdown(f"""
                <div style="background:#ffe0e0; padding:10px;
                    border-radius:8px; margin-bottom:8px;
                    text-decoration:line-through; opacity:0.7;">
                    🧾 {b.get('bill_number', '')} |
                    {name} | {pooja} |
                    {format_currency(b.get('amount', 0))} |
                    Deleted: {b.get('deleted_at', '')[:19]} |
                    Reason: {b.get('delete_reason', '-')}
                </div>
            """, unsafe_allow_html=True)

            if st.button(
                "♻️ Restore",
                key=f"restore_{b['id']}"
            ):
                db.table('bills').update({
                    'is_deleted': False,
                    'deleted_by': None,
                    'deleted_at': None,
                    'delete_reason': None
                }).eq('id', b['id']).execute()
                st.success("Bill restored!")
                time.sleep(0.5)
                st.rerun()
    else:
        st.info("No deleted bills")


# ============================================================
# MAIN APP
# ============================================================
def main():
    """Main application entry point"""
    init_session_state()
    apply_custom_css()

    # Create default admin on first run
    try:
        create_default_admin()
    except Exception:
        pass

    if not st.session_state['logged_in']:
        login_page()
    else:
        render_sidebar()

        page = st.session_state.get('current_page', 'dashboard')

        page_map = {
            'dashboard': dashboard_page,
            'devotees': devotees_page,
            'edit_devotee': devotees_page,
            'billing': billing_page,
            'expenses': expenses_page,
            'reports': reports_page,
            'samaya': samaya_vakuppu_page,
            'mandapam': thirumana_mandapam_page,
            'daily_pooja': daily_pooja_page,
            'settings': settings_page,
            'users': user_management_page,
            'deleted_bills': deleted_bills_page,
        }

        page_func = page_map.get(page, dashboard_page)
        page_func()


if __name__ == "__main__":
    main()
