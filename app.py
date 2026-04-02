"""
============================================================
 ARULMIGU BHADRESHWARI AMMAN KOVIL
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
import time

# ============================================================
# PAGE CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="Arulmigu Bhadreshwari Amman Kovil",
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
def get_supabase_client():
    """Initialize Supabase client"""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except Exception:
        st.error(
            "⚠️ Supabase credentials not found!\n\n"
            "Create file: `.streamlit/secrets.toml` with:\n\n"
            '```\nSUPABASE_URL = "https://xxxxx.supabase.co"\n'
            'SUPABASE_KEY = "your-anon-key-here"\n```'
        )
        st.stop()
    return create_client(url, key)


def get_db():
    """Get Supabase client with caching"""
    if 'db_client' not in st.session_state:
        st.session_state['db_client'] = get_supabase_client()
    return st.session_state['db_client']


# ============================================================
# PASSWORD UTILITIES
# ============================================================
def hash_password(password):
    return bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')


def check_password(password, hashed):
    try:
        return bcrypt.checkpw(
            password.encode('utf-8'),
            hashed.encode('utf-8')
        )
    except Exception:
        return False


# ============================================================
# SESSION STATE
# ============================================================
def init_session_state():
    defaults = {
        'logged_in': False,
        'user_id': None,
        'username': '',
        'full_name': '',
        'role': 'user',
        'current_page': 'dashboard',
        'dash_period': 'daily',
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
        .main-header {
            background: linear-gradient(135deg, #8B0000, #DC143C);
            color: #FFD700;
            padding: 15px 20px;
            border-radius: 12px;
            text-align: center;
            margin-bottom: 20px;
            box-shadow: 0 4px 15px rgba(139,0,0,0.3);
        }
        .main-header h1 { font-size: 1.5em; margin: 0; }
        .main-header p { font-size: 0.85em; margin: 2px 0 0 0; opacity: 0.9; }

        .stat-card {
            border-radius: 15px; padding: 20px; color: white;
            box-shadow: 0 5px 20px rgba(0,0,0,0.15);
            margin-bottom: 15px;
        }
        .stat-card.income { background: linear-gradient(135deg, #228B22, #32CD32); }
        .stat-card.expense { background: linear-gradient(135deg, #DC143C, #FF4500); }
        .stat-card.devotees { background: linear-gradient(135deg, #4169E1, #6495ED); }
        .stat-card.bills { background: linear-gradient(135deg, #FF8C00, #FFD700); }
        .stat-card h6 { font-size: 0.85em; opacity: 0.9; margin-bottom: 5px; }
        .stat-card h3 { font-size: 1.8em; font-weight: 700; margin: 0; }

        .pooja-card {
            background: linear-gradient(135deg, #FFF8DC, #FFEFD5);
            border: 1px solid #FFD700; border-radius: 10px;
            padding: 12px; margin-bottom: 8px;
            border-left: 4px solid #8B0000;
        }

        .birthday-card {
            background: #FFF8DC; border-radius: 8px;
            padding: 10px; margin-bottom: 8px;
            border-left: 3px solid #DC143C;
        }

        .bill-header {
            text-align: center;
            border-bottom: 3px double #8B0000;
            padding-bottom: 12px; margin-bottom: 15px;
        }
        .bill-header h3 { color: #8B0000; margin: 0; font-weight: 700; }
        .bill-header h5 { color: #DC143C; margin: 2px 0; }
        .bill-header p { color: #555; font-size: 0.85em; margin: 1px 0; }

        div[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #8B0000, #B22222, #DC143C);
        }
        div[data-testid="stSidebar"] * { color: #FFD700 !important; }

        .stButton>button {
            background: linear-gradient(135deg, #8B0000, #DC143C);
            color: white !important; border: none;
            border-radius: 8px; font-weight: 500;
        }
        .stButton>button:hover {
            background: linear-gradient(135deg, #DC143C, #FF4500);
            box-shadow: 0 4px 12px rgba(220,20,60,0.4);
        }
    </style>
    """, unsafe_allow_html=True)


# ============================================================
# HELPER FUNCTIONS
# ============================================================
def generate_bill_number():
    db = get_db()
    today = date.today()
    prefix = f"BILL-{today.strftime('%Y%m%d')}"
    try:
        result = db.table('bills').select('bill_number').like(
            'bill_number', f'{prefix}%'
        ).execute()
        count = len(result.data) + 1
    except Exception:
        count = 1
    return f"{prefix}-{count:04d}"


def get_period_dates(period):
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


def format_currency(amount):
    if amount is None:
        amount = 0
    return f"₹{amount:,.2f}"


# ============================================================
# CREATE DEFAULT ADMIN
# ============================================================
def create_default_admin():
    db = get_db()
    try:
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
    except Exception as e:
        pass


# ============================================================
# LOGIN PAGE
# ============================================================
def login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"""
            <div style="text-align:center; padding:20px;
                        background:white; border-radius:20px;
                        box-shadow:0 10px 40px rgba(0,0,0,0.1);
                        margin-top:30px;">
                <h1 style="font-size:3em;">🕉️</h1>
                <h2 style="color:#8B0000; font-weight:700;">
                    {TEMPLE_NAME}
                </h2>
                <p style="color:#DC143C; font-weight:600;">
                    {TEMPLE_ADDRESS_LINE2}
                </p>
                <p style="color:#666; font-size:0.9em;">
                    {TEMPLE_ADDRESS_LINE3}
                </p>
                <hr style="border-color:#FFD700;">
            </div>
        """, unsafe_allow_html=True)

        st.markdown("")
        st.markdown("### 🔐 Login to Continue")

        with st.form("login_form"):
            username = st.text_input(
                "👤 Username",
                placeholder="Enter username"
            )
            password = st.text_input(
                "🔒 Password",
                type="password",
                placeholder="Enter password"
            )
            submitted = st.form_submit_button(
                "🔑 Login",
                use_container_width=True
            )

            if submitted:
                if not username or not password:
                    st.error("Please enter both username and password!")
                    return

                db = get_db()
                try:
                    result = db.table('users').select('*').eq(
                        'username', username
                    ).execute()

                    if result.data:
                        user = result.data[0]
                        if check_password(
                            password, user['password_hash']
                        ):
                            if user.get('is_active_user', True):
                                st.session_state['logged_in'] = True
                                st.session_state['user_id'] = user['id']
                                st.session_state['username'] = user['username']
                                st.session_state['full_name'] = (
                                    user.get('full_name') or user['username']
                                )
                                st.session_state['role'] = user.get(
                                    'role', 'user'
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
                except Exception as e:
                    st.error(f"❌ Database error: {e}")

        st.markdown("""
            <div style="text-align:center; margin-top:20px;">
                <small style="color:#aaa;">
                    🕉️ Temple Management System<br>
                    Default login: admin / admin123
                </small>
            </div>
        """, unsafe_allow_html=True)


# ============================================================
# SIDEBAR NAVIGATION
# ============================================================
def render_sidebar():
    with st.sidebar:
        st.markdown(f"""
            <div style="text-align:center; padding:10px;">
                <h2>🕉️</h2>
                <h4>{TEMPLE_NAME}</h4>
                <p style="font-size:0.7em; opacity:0.8;">
                    {TEMPLE_TRUST}
                </p>
                <p style="font-size:0.75em;">
                    👤 {st.session_state['full_name']}
                    {'🔑 ADMIN' if st.session_state['role'] == 'admin' else ''}
                </p>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        pages = [
            ("📊 Dashboard", "dashboard"),
            ("👥 Devotees", "devotees"),
            ("🧾 Billing", "billing"),
            ("💰 Expenses", "expenses"),
            ("📈 Reports", "reports"),
            ("🎓 Samaya Vakuppu", "samaya"),
            ("🏛️ Thirumana Mandapam", "mandapam"),
            ("🙏 Daily Pooja", "daily_pooja"),
            ("⚙️ Settings", "settings"),
        ]

        if st.session_state['role'] == 'admin':
            pages.append(("👤 User Management", "users"))
            pages.append(("🗑️ Deleted Bills", "deleted_bills"))

        for label, page_key in pages:
            if st.button(label, key=f"nav_{page_key}",
                         use_container_width=True):
                st.session_state['current_page'] = page_key
                st.rerun()

        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()


# ============================================================
# DASHBOARD PAGE
# ============================================================
def dashboard_page():
    db = get_db()

    st.markdown(f"""
        <div class="main-header">
            <h1>🕉️ {TEMPLE_NAME}</h1>
            <p>{TEMPLE_ADDRESS_LINE2} | {TEMPLE_ADDRESS_LINE3}</p>
            <p>📅 {datetime.now().strftime('%d %B %Y, %A')}</p>
        </div>
    """, unsafe_allow_html=True)

    # Period selector
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("📅 Daily", use_container_width=True):
            st.session_state['dash_period'] = 'daily'
            st.rerun()
    with c2:
        if st.button("📆 Weekly", use_container_width=True):
            st.session_state['dash_period'] = 'weekly'
            st.rerun()
    with c3:
        if st.button("🗓️ Monthly", use_container_width=True):
            st.session_state['dash_period'] = 'monthly'
            st.rerun()
    with c4:
        if st.button("📊 Yearly", use_container_width=True):
            st.session_state['dash_period'] = 'yearly'
            st.rerun()

    period = st.session_state.get('dash_period', 'daily')
    start_date, end_date = get_period_dates(period)

    st.info(f"📅 Showing: **{period.upper()}** | {start_date} to {end_date}")

    # Fetch stats
    try:
        bills_result = db.table('bills').select('amount').eq(
            'is_deleted', False
        ).gte(
            'bill_date', start_date.isoformat()
        ).lte(
            'bill_date', end_date.isoformat() + "T23:59:59"
        ).execute()
        total_income = sum(
            b.get('amount', 0) or 0 for b in bills_result.data
        )
        total_bills = len(bills_result.data)
    except Exception:
        total_income = 0
        total_bills = 0

    try:
        expenses_result = db.table('expenses').select('amount').gte(
            'expense_date', start_date.isoformat()
        ).lte(
            'expense_date', end_date.isoformat()
        ).execute()
        total_expenses = sum(
            e.get('amount', 0) or 0 for e in expenses_result.data
        )
    except Exception:
        total_expenses = 0

    try:
        dev_result = db.table('devotees').select(
            'id', count='exact'
        ).eq('is_active', True).eq('is_family_head', True).execute()
        total_devotees = dev_result.count or 0
    except Exception:
        total_devotees = 0

    # Display stat cards
    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.markdown(f"""
            <div class="stat-card income">
                <h6>📈 {period.title()} Income</h6>
                <h3>{format_currency(total_income)}</h3>
            </div>
        """, unsafe_allow_html=True)
    with s2:
        st.markdown(f"""
            <div class="stat-card expense">
                <h6>📉 {period.title()} Expenses</h6>
                <h3>{format_currency(total_expenses)}</h3>
            </div>
        """, unsafe_allow_html=True)
    with s3:
        st.markdown(f"""
            <div class="stat-card devotees">
                <h6>👥 Total Devotees</h6>
                <h3>{total_devotees}</h3>
            </div>
        """, unsafe_allow_html=True)
    with s4:
        st.markdown(f"""
            <div class="stat-card bills">
                <h6>🧾 {period.title()} Bills</h6>
                <h3>{total_bills}</h3>
            </div>
        """, unsafe_allow_html=True)

    # Two columns
    left_col, right_col = st.columns(2)

    with left_col:
        st.markdown("### 🙏 Today's Pooja Schedule")
        try:
            poojas = db.table('daily_poojas').select('*').eq(
                'is_active', True
            ).order('pooja_time').execute()
            if poojas.data:
                for p in poojas.data:
                    st.markdown(f"""
                        <div class="pooja-card">
                            <strong>{p['pooja_name']}</strong>
                            <span style="float:right; color:#8B0000;
                                font-weight:700;">
                                {p.get('pooja_time', 'TBD')}
                            </span><br>
                            <small style="color:#666;">
                                {p.get('description', '')}
                            </small>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No pooja scheduled")
        except Exception:
            st.info("No pooja data")

    with right_col:
        st.markdown("### 🎂 Today's Birthdays")
        try:
            today = date.today()
            all_dev = db.table('devotees').select(
                'name, dob, mobile_no'
            ).eq('is_active', True).execute()

            bdays = []
            for d in all_dev.data:
                if d.get('dob'):
                    try:
                        dob = datetime.strptime(
                            d['dob'], '%Y-%m-%d'
                        ).date()
                        if dob.month == today.month and dob.day == today.day:
                            bdays.append(d)
                    except (ValueError, TypeError):
                        pass

            if bdays:
                for b in bdays:
                    st.markdown(f"""
                        <div class="birthday-card">
                            🎂 <strong>{b['name']}</strong><br>
                            <small>📱 {b.get('mobile_no', '-')}</small>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No birthdays today")
        except Exception:
            st.info("No birthday data")

    # Recent Bills
    st.markdown("### 🧾 Recent Bills")
    try:
        recent = db.table('bills').select(
            '*, devotees(name), pooja_types(name)'
        ).eq('is_deleted', False).order(
            'created_at', desc=True
        ).limit(10).execute()

        if recent.data:
            rows = []
            for b in recent.data:
                name = ""
                if b.get('devotees'):
                    name = b['devotees'].get('name', '')
                elif b.get('guest_name'):
                    name = b['guest_name']
                pooja = ""
                if b.get('pooja_types'):
                    pooja = b['pooja_types'].get('name', '')

                rows.append({
                    'Bill No': b.get('bill_number', ''),
                    'Date': str(b.get('bill_date', ''))[:10],
                    'Name': name,
                    'Pooja': pooja,
                    'Amount': format_currency(b.get('amount', 0))
                })
            st.dataframe(
                pd.DataFrame(rows),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No bills yet")
    except Exception as e:
        st.info(f"No bill data: {e}")


# ============================================================
# DEVOTEES PAGE
# ============================================================
def devotees_page():
    db = get_db()

    st.markdown("""
        <div class="main-header">
            <h1>👥 Devotee Management</h1>
        </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs([
        "📋 All Devotees", "➕ Add Devotee", "🔍 Search"
    ])

    # TAB 1 - LIST
    with tab1:
        try:
            devotees = db.table('devotees').select('*').eq(
                'is_active', True
            ).eq('is_family_head', True).order('name').execute()

            if devotees.data:
                st.success(f"Total: {len(devotees.data)} devotees")

                for d in devotees.data:
                    with st.expander(
                        f"👤 {d['name']} | 📱 {d.get('mobile_no', '-')} "
                        f"| ⭐ {d.get('natchathiram', '-')}"
                    ):
                        c1, c2 = st.columns(2)
                        with c1:
                            st.write(f"**Name:** {d['name']}")
                            st.write(f"**DOB:** {d.get('dob', '-')}")
                            st.write(f"**Mobile:** {d.get('mobile_no', '-')}")
                            st.write(f"**WhatsApp:** {d.get('whatsapp_no', '-')}")
                            st.write(f"**Address:** {d.get('address', '-')}")
                        with c2:
                            st.write(f"**Natchathiram:** {d.get('natchathiram', '-')}")
                            st.write(f"**Relation:** {d.get('relation_type', '-')}")
                            st.write(f"**Wedding Day:** {d.get('wedding_day', '-')}")

                        # Family members
                        try:
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
                        except Exception:
                            pass

                        # Yearly poojas
                        try:
                            yearly = db.table(
                                'devotee_yearly_poojas'
                            ).select(
                                '*, pooja_types(name)'
                            ).eq('devotee_id', d['id']).execute()
                            if yearly.data:
                                st.markdown("**🙏 Yearly Poojas:**")
                                for yp in yearly.data:
                                    pn = ""
                                    if yp.get('pooja_types'):
                                        pn = yp['pooja_types'].get('name', '')
                                    st.write(
                                        f"  - {pn} | "
                                        f"Date: {yp.get('pooja_date', '-')} | "
                                        f"Notes: {yp.get('notes', '-')}"
                                    )
                        except Exception:
                            pass

                        # Delete button
                        if st.button("🗑️ Delete Devotee",
                                     key=f"del_d_{d['id']}"):
                            db.table('devotees').update(
                                {'is_active': False}
                            ).eq('id', d['id']).execute()
                            st.success("Deleted!")
                            time.sleep(0.5)
                            st.rerun()
            else:
                st.info("No devotees found. Add your first devotee!")
        except Exception as e:
            st.error(f"Error loading devotees: {e}")

    # TAB 2 - ADD
    with tab2:
        with st.form("add_devotee_form"):
            st.markdown("#### 👤 Devotee Details")
            c1, c2 = st.columns(2)
            with c1:
                name = st.text_input("Name *")
                dob = st.date_input(
                    "Date of Birth", value=None,
                    min_value=date(1920, 1, 1),
                    max_value=date.today()
                )
                mobile = st.text_input("Mobile Number")
                whatsapp = st.text_input("WhatsApp Number")
            with c2:
                relation = st.selectbox(
                    "Relation Type", [''] + RELATION_TYPES
                )
                natchathiram = st.selectbox(
                    "Natchathiram", [''] + NATCHATHIRAM_LIST
                )
                wedding = st.date_input(
                    "Wedding Day", value=None,
                    min_value=date(1950, 1, 1)
                )

            address = st.text_area("Address")

            # Family members
            st.markdown("---")
            st.markdown("#### 👨‍👩‍👧‍👦 Family Members")
            num_fm = st.number_input(
                "Number of family members", 0, 20, 0
            )
            family_data = []
            for i in range(int(num_fm)):
                st.markdown(f"**Member {i+1}**")
                fc1, fc2, fc3 = st.columns(3)
                with fc1:
                    fm_name = st.text_input("Name", key=f"fm_n_{i}")
                with fc2:
                    fm_dob = st.date_input(
                        "DOB", value=None, key=f"fm_d_{i}",
                        min_value=date(1920, 1, 1)
                    )
                with fc3:
                    fm_rel = st.selectbox(
                        "Relation", [''] + RELATION_TYPES,
                        key=f"fm_r_{i}"
                    )
                family_data.append({
                    'name': fm_name, 'dob': fm_dob, 'relation': fm_rel
                })

            # Yearly poojas
            st.markdown("---")
            st.markdown("#### 🙏 Yearly Poojas")
            try:
                pt_result = db.table('pooja_types').select('*').eq(
                    'is_active', True
                ).execute()
                pooja_types = pt_result.data
            except Exception:
                pooja_types = []

            num_yp = st.number_input(
                "Number of yearly poojas", 0, 20, 0
            )
            pooja_data = []
            for i in range(int(num_yp)):
                pc1, pc2, pc3 = st.columns(3)
                with pc1:
                    pt_sel = st.selectbox(
                        "Pooja", [''] + [p['name'] for p in pooja_types],
                        key=f"yp_t_{i}"
                    )
                with pc2:
                    yp_date = st.date_input(
                        "Date", value=None, key=f"yp_d_{i}"
                    )
                with pc3:
                    yp_notes = st.text_input("Notes", key=f"yp_n_{i}")

                pt_id = None
                for p in pooja_types:
                    if p['name'] == pt_sel:
                        pt_id = p['id']
                        break
                pooja_data.append({
                    'pooja_type_id': pt_id, 'pooja_name': pt_sel,
                    'pooja_date': yp_date, 'notes': yp_notes
                })

            submitted = st.form_submit_button(
                "💾 Save Devotee", use_container_width=True
            )

            if submitted:
                if not name:
                    st.error("Name is required!")
                else:
                    try:
                        result = db.table('devotees').insert({
                            'name': name,
                            'dob': dob.isoformat() if dob else None,
                            'relation_type': relation or None,
                            'mobile_no': mobile or None,
                            'whatsapp_no': whatsapp or None,
                            'wedding_day': wedding.isoformat() if wedding else None,
                            'natchathiram': natchathiram or None,
                            'address': address or None,
                            'is_family_head': True,
                            'is_active': True
                        }).execute()
                        dev_id = result.data[0]['id']

                        # Family members
                        for fm in family_data:
                            if fm['name']:
                                db.table('devotees').insert({
                                    'name': fm['name'],
                                    'dob': fm['dob'].isoformat() if fm['dob'] else None,
                                    'relation_type': fm['relation'] or None,
                                    'is_family_head': False,
                                    'family_head_id': dev_id,
                                    'is_active': True
                                }).execute()

                        # Yearly poojas
                        for yp in pooja_data:
                            if yp['pooja_type_id'] or yp['pooja_name']:
                                db.table('devotee_yearly_poojas').insert({
                                    'devotee_id': dev_id,
                                    'pooja_type_id': yp['pooja_type_id'],
                                    'pooja_name': yp['pooja_name'],
                                    'pooja_date': yp['pooja_date'].isoformat() if yp['pooja_date'] else None,
                                    'notes': yp['notes'] or None
                                }).execute()

                        st.success("✅ Devotee added successfully!")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

    # TAB 3 - SEARCH
    with tab3:
        search = st.text_input("🔍 Search by Name or Mobile")
        if search:
            try:
                results = db.table('devotees').select('*').eq(
                    'is_active', True
                ).or_(
                    f"name.ilike.%{search}%,mobile_no.ilike.%{search}%"
                ).execute()
                if results.data:
                    for d in results.data:
                        st.write(
                            f"👤 **{d['name']}** | "
                            f"📱 {d.get('mobile_no', '-')} | "
                            f"⭐ {d.get('natchathiram', '-')} | "
                            f"Head: {'Yes' if d.get('is_family_head') else 'No'}"
                        )
                else:
                    st.warning("No results found")
            except Exception as e:
                st.error(f"Search error: {e}")


# ============================================================
# BILLING PAGE
# ============================================================
def billing_page():
    db = get_db()

    st.markdown("""
        <div class="main-header"><h1>🧾 Billing</h1></div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📋 Bills List", "➕ New Bill"])

    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            from_date = st.date_input("From", value=date.today(), key="bf")
        with c2:
            to_date = st.date_input("To", value=date.today(), key="bt")

        try:
            bills = db.table('bills').select(
                '*, devotees(name), pooja_types(name)'
            ).eq('is_deleted', False).gte(
                'bill_date', from_date.isoformat()
            ).lte(
                'bill_date', to_date.isoformat() + "T23:59:59"
            ).order('created_at', desc=True).execute()

            if bills.data:
                total = sum(b.get('amount', 0) or 0 for b in bills.data)
                st.success(
                    f"Total: {format_currency(total)} | "
                    f"Bills: {len(bills.data)}"
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
                        f"🧾 {b.get('bill_number', '')} | {name} | "
                        f"{pooja} | {format_currency(b.get('amount', 0))}"
                    ):
                        c1, c2 = st.columns(2)
                        with c1:
                            st.write(f"**Bill No:** {b.get('bill_number', '')}")
                            st.write(f"**Manual:** {b.get('manual_bill_no', '-')}")
                            st.write(f"**Name:** {name}")
                            st.write(f"**Pooja:** {pooja}")
                        with c2:
                            st.write(f"**Amount:** {format_currency(b.get('amount', 0))}")
                            st.write(f"**Date:** {str(b.get('bill_date', ''))[:10]}")
                            st.write(f"**Notes:** {b.get('notes', '-')}")

                        # Delete (admin)
                        if st.session_state['role'] == 'admin':
                            reason = st.text_input(
                                "Delete reason",
                                key=f"dr_{b['id']}"
                            )
                            if st.button(
                                "🗑️ Delete Bill",
                                key=f"db_{b['id']}"
                            ):
                                if reason:
                                    db.table('bills').update({
                                        'is_deleted': True,
                                        'deleted_by': st.session_state['user_id'],
                                        'deleted_at': datetime.now().isoformat(),
                                        'delete_reason': reason
                                    }).eq('id', b['id']).execute()
                                    st.success("Deleted!")
                                    time.sleep(0.5)
                                    st.rerun()
                                else:
                                    st.warning("Enter delete reason!")
            else:
                st.info("No bills for selected period")
        except Exception as e:
            st.error(f"Error: {e}")

    with tab2:
        try:
            pooja_types = db.table('pooja_types').select('*').eq(
                'is_active', True
            ).execute().data
        except Exception:
            pooja_types = []

        with st.form("new_bill"):
            st.markdown("#### 🧾 New Bill")
            c1, c2 = st.columns(2)
            with c1:
                manual_bill = st.text_input("Manual Bill No")
                bill_book = st.text_input("Bill Book No")
                bill_date = st.date_input("Bill Date", value=date.today())
            with c2:
                dev_type = st.radio(
                    "Type", ['Enrolled', 'Guest'], horizontal=True
                )

            if dev_type == 'Enrolled':
                try:
                    devs = db.table('devotees').select(
                        'id, name, mobile_no'
                    ).eq('is_active', True).eq(
                        'is_family_head', True
                    ).order('name').execute()
                    dev_opts = {
                        f"{d['name']} ({d.get('mobile_no', '-')})": d['id']
                        for d in devs.data
                    }
                except Exception:
                    dev_opts = {}

                sel = st.selectbox(
                    "Select Devotee", [''] + list(dev_opts.keys())
                )
                devotee_id = dev_opts.get(sel)
                guest_name = guest_address = guest_mobile = guest_whatsapp = None
            else:
                devotee_id = None
                guest_name = st.text_input("Guest Name *")
                guest_address = st.text_area("Guest Address")
                gc1, gc2 = st.columns(2)
                with gc1:
                    guest_mobile = st.text_input("Guest Mobile")
                with gc2:
                    guest_whatsapp = st.text_input("Guest WhatsApp")

            pooja_opts = {p['name']: p for p in pooja_types}
            sel_pooja = st.selectbox(
                "Pooja Type *", [''] + list(pooja_opts.keys())
            )

            default_amt = 0.0
            if sel_pooja and sel_pooja in pooja_opts:
                default_amt = pooja_opts[sel_pooja].get('amount', 0)

            amount = st.number_input(
                "Amount (₹)", value=float(default_amt),
                min_value=0.0, step=10.0
            )
            notes = st.text_area("Notes")

            if st.form_submit_button(
                "💾 Create Bill", use_container_width=True
            ):
                if dev_type == 'Enrolled' and not devotee_id:
                    st.error("Select a devotee!")
                elif dev_type == 'Guest' and not guest_name:
                    st.error("Enter guest name!")
                elif not sel_pooja:
                    st.error("Select pooja type!")
                else:
                    try:
                        bill_number = generate_bill_number()
                        pt_id = None
                        if sel_pooja in pooja_opts:
                            pt_id = pooja_opts[sel_pooja]['id']

                        db.table('bills').insert({
                            'bill_number': bill_number,
                            'manual_bill_no': manual_bill or None,
                            'bill_book_no': bill_book or None,
                            'bill_date': datetime.combine(
                                bill_date, datetime.now().time()
                            ).isoformat(),
                            'devotee_type': dev_type.lower(),
                            'devotee_id': devotee_id,
                            'guest_name': guest_name,
                            'guest_address': guest_address,
                            'guest_mobile': guest_mobile,
                            'guest_whatsapp': guest_whatsapp,
                            'pooja_type_id': pt_id,
                            'amount': amount,
                            'notes': notes or None,
                            'is_deleted': False,
                            'created_by': st.session_state['user_id']
                        }).execute()

                        st.success(f"✅ Bill {bill_number} created!")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")


# ============================================================
# EXPENSES PAGE
# ============================================================
def expenses_page():
    db = get_db()

    st.markdown("""
        <div class="main-header"><h1>💰 Expenses</h1></div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📋 List", "➕ Add"])

    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            ef = st.date_input(
                "From", value=date.today().replace(day=1), key="ef"
            )
        with c2:
            et = st.date_input("To", value=date.today(), key="et")

        try:
            expenses = db.table('expenses').select(
                '*, expense_types(name)'
            ).gte(
                'expense_date', ef.isoformat()
            ).lte(
                'expense_date', et.isoformat()
            ).order('expense_date', desc=True).execute()

            if expenses.data:
                total = sum(
                    e.get('amount', 0) or 0 for e in expenses.data
                )
                st.success(f"Total: {format_currency(total)}")

                rows = []
                for e in expenses.data:
                    etype = ""
                    if e.get('expense_types'):
                        etype = e['expense_types'].get('name', '')
                    rows.append({
                        'Date': e.get('expense_date', ''),
                        'Type': etype,
                        'Description': e.get('description', ''),
                        'Amount': format_currency(e.get('amount', 0))
                    })
                st.dataframe(
                    pd.DataFrame(rows),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No expenses")
        except Exception as e:
            st.error(f"Error: {e}")

    with tab2:
        try:
            exp_types = db.table('expense_types').select('*').eq(
                'is_active', True
            ).execute().data
        except Exception:
            exp_types = []

        with st.form("add_exp"):
            c1, c2 = st.columns(2)
            with c1:
                et_opts = {e['name']: e['id'] for e in exp_types}
                sel_et = st.selectbox(
                    "Type *", [''] + list(et_opts.keys())
                )
                amt = st.number_input(
                    "Amount *", min_value=0.0, step=10.0
                )
            with c2:
                ed = st.date_input("Date", value=date.today())
                desc = st.text_area("Description")

            if st.form_submit_button(
                "💾 Add", use_container_width=True
            ):
                if not sel_et or amt <= 0:
                    st.error("Select type and enter amount!")
                else:
                    try:
                        db.table('expenses').insert({
                            'expense_type_id': et_opts[sel_et],
                            'amount': amt,
                            'description': desc or None,
                            'expense_date': ed.isoformat(),
                            'created_by': st.session_state['user_id']
                        }).execute()
                        st.success("✅ Added!")
                        time.sleep(0.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")


# ============================================================
# REPORTS PAGE
# ============================================================
def reports_page():
    db = get_db()

    st.markdown("""
        <div class="main-header"><h1>📈 Reports</h1></div>
    """, unsafe_allow_html=True)

    report = st.selectbox("Report Type", [
        "Income Summary", "Expense Summary",
        "Income vs Expense", "Pooja-wise Income"
    ])

    c1, c2 = st.columns(2)
    with c1:
        rf = st.date_input(
            "From", value=date.today().replace(month=1, day=1), key="rf"
        )
    with c2:
        rt = st.date_input("To", value=date.today(), key="rt")

    try:
        if report == "Income Summary":
            bills = db.table('bills').select('amount, bill_date').eq(
                'is_deleted', False
            ).gte('bill_date', rf.isoformat()).lte(
                'bill_date', rt.isoformat() + "T23:59:59"
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
                st.metric("Total", format_currency(df['amount'].sum()))
            else:
                st.info("No data")

        elif report == "Expense Summary":
            exps = db.table('expenses').select(
                '*, expense_types(name)'
            ).gte('expense_date', rf.isoformat()).lte(
                'expense_date', rt.isoformat()
            ).execute()

            if exps.data:
                data = []
                for e in exps.data:
                    et = ""
                    if e.get('expense_types'):
                        et = e['expense_types'].get('name', '')
                    data.append({'type': et, 'amount': e.get('amount', 0)})
                df = pd.DataFrame(data)
                ts = df.groupby('type')['amount'].sum().reset_index()
                fig = px.pie(
                    ts, values='amount', names='type',
                    title="Expense Breakdown"
                )
                st.plotly_chart(fig, use_container_width=True)
                st.metric("Total", format_currency(df['amount'].sum()))
            else:
                st.info("No data")

        elif report == "Income vs Expense":
            bills = db.table('bills').select('amount').eq(
                'is_deleted', False
            ).gte('bill_date', rf.isoformat()).lte(
                'bill_date', rt.isoformat() + "T23:59:59"
            ).execute()
            exps = db.table('expenses').select('amount').gte(
                'expense_date', rf.isoformat()
            ).lte('expense_date', rt.isoformat()).execute()

            inc = sum(b.get('amount', 0) or 0 for b in bills.data)
            exp = sum(e.get('amount', 0) or 0 for e in exps.data)

            fig = go.Figure(data=[
                go.Bar(name='Income', x=['Income'], y=[inc],
                       marker_color='#228B22'),
                go.Bar(name='Expense', x=['Expense'], y=[exp],
                       marker_color='#DC143C')
            ])
            fig.update_layout(title="Income vs Expense")
            st.plotly_chart(fig, use_container_width=True)

            m1, m2, m3 = st.columns(3)
            with m1: st.metric("Income", format_currency(inc))
            with m2: st.metric("Expenses", format_currency(exp))
            with m3: st.metric("Net", format_currency(inc - exp))

        elif report == "Pooja-wise Income":
            bills = db.table('bills').select(
                'amount, pooja_types(name)'
            ).eq('is_deleted', False).gte(
                'bill_date', rf.isoformat()
            ).lte('bill_date', rt.isoformat() + "T23:59:59").execute()

            if bills.data:
                data = []
                for b in bills.data:
                    pn = ""
                    if b.get('pooja_types'):
                        pn = b['pooja_types'].get('name', '')
                    data.append({'pooja': pn, 'amount': b.get('amount', 0)})
                df = pd.DataFrame(data)
                ps = df.groupby('pooja')['amount'].sum().reset_index()
                fig = px.bar(
                    ps, x='pooja', y='amount',
                    title="Pooja-wise Income",
                    color_discrete_sequence=['#8B0000']
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data")
    except Exception as e:
        st.error(f"Error: {e}")


# ============================================================
# SAMAYA VAKUPPU PAGE
# ============================================================
def samaya_page():
    db = get_db()

    st.markdown("""
        <div class="main-header"><h1>🎓 Samaya Vakuppu</h1></div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📋 Students", "➕ Add"])

    with tab1:
        try:
            students = db.table('samaya_vakuppu').select('*').order(
                'student_name'
            ).execute()
            if students.data:
                for s in students.data:
                    with st.expander(
                        f"🎓 {s['student_name']} | Bond: {s.get('bond_no', '-')}"
                    ):
                        c1, c2 = st.columns(2)
                        with c1:
                            st.write(f"**Name:** {s['student_name']}")
                            st.write(f"**DOB:** {s.get('dob', '-')}")
                            st.write(f"**Parent:** {s.get('father_mother_name', '-')}")
                            st.write(f"**Address:** {s.get('address', '-')}")
                        with c2:
                            st.write(f"**Bond No:** {s.get('bond_no', '-')}")
                            st.write(f"**Bond Date:** {s.get('bond_issue_date', '-')}")
                            st.write(f"**Bank:** {s.get('bond_issuing_bank', '-')}")
                            st.write(f"**Branch:** {s.get('branch_of_bank', '-')}")

                        if st.button("🗑️ Delete", key=f"ds_{s['id']}"):
                            db.table('samaya_vakuppu').delete().eq(
                                'id', s['id']
                            ).execute()
                            st.success("Deleted!")
                            time.sleep(0.5)
                            st.rerun()
            else:
                st.info("No students")
        except Exception as e:
            st.error(f"Error: {e}")

    with tab2:
        with st.form("add_sam"):
            c1, c2 = st.columns(2)
            with c1:
                sn = st.text_input("Student Name *")
                sd = st.date_input("DOB", value=None, key="sd",
                                   min_value=date(1950, 1, 1))
                sp = st.text_input("Father/Mother Name")
                sa = st.text_area("Address")
            with c2:
                sb = st.text_input("Bond No")
                sbd = st.date_input("Bond Date", value=None, key="sbd")
                sbk = st.text_input("Bank")
                sbr = st.text_input("Branch")

            if st.form_submit_button("💾 Save", use_container_width=True):
                if not sn:
                    st.error("Name required!")
                else:
                    try:
                        db.table('samaya_vakuppu').insert({
                            'student_name': sn,
                            'dob': sd.isoformat() if sd else None,
                            'father_mother_name': sp or None,
                            'address': sa or None,
                            'bond_no': sb or None,
                            'bond_issue_date': sbd.isoformat() if sbd else None,
                            'bond_issuing_bank': sbk or None,
                            'branch_of_bank': sbr or None
                        }).execute()
                        st.success("✅ Added!")
                        time.sleep(0.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")


# ============================================================
# THIRUMANA MANDAPAM PAGE
# ============================================================
def mandapam_page():
    db = get_db()

    st.markdown("""
        <div class="main-header"><h1>🏛️ Thirumana Mandapam</h1></div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📋 Records", "➕ Add"])

    with tab1:
        try:
            records = db.table('thirumana_mandapam').select('*').order(
                'name'
            ).execute()
            if records.data:
                for r in records.data:
                    with st.expander(
                        f"🏛️ {r['name']} | Bond: {r.get('bond_no', '-')} "
                        f"| {format_currency(r.get('amount', 0))}"
                    ):
                        c1, c2 = st.columns(2)
                        with c1:
                            st.write(f"**Name:** {r['name']}")
                            st.write(f"**Address:** {r.get('address', '-')}")
                            st.write(f"**Bond No:** {r.get('bond_no', '-')}")
                        with c2:
                            st.write(f"**Date:** {r.get('bond_issued_date', '-')}")
                            st.write(f"**Amount:** {format_currency(r.get('amount', 0))}")
                            st.write(f"**Bonds:** {r.get('no_of_bond', 1)}")

                        if st.button("🗑️ Delete", key=f"dm_{r['id']}"):
                            db.table('thirumana_mandapam').delete().eq(
                                'id', r['id']
                            ).execute()
                            st.success("Deleted!")
                            time.sleep(0.5)
                            st.rerun()
            else:
                st.info("No records")
        except Exception as e:
            st.error(f"Error: {e}")

    with tab2:
        with st.form("add_mand"):
            c1, c2 = st.columns(2)
            with c1:
                mn = st.text_input("Name *")
                ma = st.text_area("Address")
                mb = st.text_input("Bond No")
            with c2:
                md = st.date_input("Bond Date", value=None, key="md")
                mamt = st.number_input("Amount", min_value=0.0, step=100.0)
                mc = st.number_input("No of Bonds", min_value=1, value=1)

            if st.form_submit_button("�� Save", use_container_width=True):
                if not mn:
                    st.error("Name required!")
                else:
                    try:
                        db.table('thirumana_mandapam').insert({
                            'name': mn,
                            'address': ma or None,
                            'bond_no': mb or None,
                            'bond_issued_date': md.isoformat() if md else None,
                            'amount': mamt,
                            'no_of_bond': mc
                        }).execute()
                        st.success("✅ Added!")
                        time.sleep(0.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")


# ============================================================
# DAILY POOJA PAGE
# ============================================================
def daily_pooja_page():
    db = get_db()

    st.markdown("""
        <div class="main-header"><h1>🙏 Daily Pooja</h1></div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📋 Schedule", "➕ Add"])

    with tab1:
        try:
            poojas = db.table('daily_poojas').select('*').order(
                'pooja_time'
            ).execute()
            if poojas.data:
                for p in poojas.data:
                    icon = "🟢" if p.get('is_active') else "🔴"
                    st.markdown(f"""
                        <div class="pooja-card">
                            <strong>{icon} {p['pooja_name']}</strong>
                            <span style="float:right; color:#8B0000;
                                font-weight:700;">{p.get('pooja_time', 'TBD')}</span>
                            <br><small style="color:#666;">
                                {p.get('description', '')}</small>
                        </div>
                    """, unsafe_allow_html=True)

                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("🔄 Toggle", key=f"tp_{p['id']}"):
                            db.table('daily_poojas').update({
                                'is_active': not p.get('is_active', True)
                            }).eq('id', p['id']).execute()
                            st.rerun()
                    with c2:
                        if st.button("🗑️ Delete", key=f"dp_{p['id']}"):
                            db.table('daily_poojas').delete().eq(
                                'id', p['id']
                            ).execute()
                            st.rerun()
            else:
                st.info("No poojas")
        except Exception as e:
            st.error(f"Error: {e}")

    with tab2:
        with st.form("add_pooja"):
            pn = st.text_input("Pooja Name *")
            pt = st.text_input("Time (e.g., 06:00 AM)")
            pd_desc = st.text_area("Description")
            if st.form_submit_button("💾 Save", use_container_width=True):
                if not pn:
                    st.error("Name required!")
                else:
                    try:
                        db.table('daily_poojas').insert({
                            'pooja_name': pn,
                            'pooja_time': pt or None,
                            'description': pd_desc or None,
                            'is_active': True
                        }).execute()
                        st.success("✅ Added!")
                        time.sleep(0.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")


# ============================================================
# SETTINGS PAGE
# ============================================================
def settings_page():
    db = get_db()

    st.markdown("""
        <div class="main-header"><h1>⚙️ Settings</h1></div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs([
        "🙏 Pooja Types", "💰 Expense Types", "🔑 Password"
    ])

    with tab1:
        try:
            pts = db.table('pooja_types').select('*').order('name').execute()
            if pts.data:
                for pt in pts.data:
                    c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                    with c1: st.write(pt['name'])
                    with c2: st.write(format_currency(pt.get('amount', 0)))
                    with c3: st.write("✅" if pt.get('is_active') else "❌")
                    with c4:
                        if st.button("🔄", key=f"tpt_{pt['id']}"):
                            db.table('pooja_types').update({
                                'is_active': not pt.get('is_active', True)
                            }).eq('id', pt['id']).execute()
                            st.rerun()
        except Exception:
            pass

        st.markdown("---")
        with st.form("add_pt"):
            c1, c2 = st.columns(2)
            with c1: ptn = st.text_input("Pooja Name *")
            with c2: pta = st.number_input("Amount", min_value=0.0, step=10.0)
            if st.form_submit_button("💾 Add"):
                if ptn:
                    db.table('pooja_types').insert({
                        'name': ptn, 'amount': pta, 'is_active': True
                    }).execute()
                    st.success("Added!")
                    time.sleep(0.5)
                    st.rerun()

    with tab2:
        try:
            ets = db.table('expense_types').select('*').order('name').execute()
            if ets.data:
                for et in ets.data:
                    c1, c2, c3 = st.columns([4, 1, 1])
                    with c1: st.write(et['name'])
                    with c2: st.write("✅" if et.get('is_active') else "❌")
                    with c3:
                        if st.button("🔄", key=f"tet_{et['id']}"):
                            db.table('expense_types').update({
                                'is_active': not et.get('is_active', True)
                            }).eq('id', et['id']).execute()
                            st.rerun()
        except Exception:
            pass

        st.markdown("---")
        with st.form("add_et"):
            etn = st.text_input("Expense Type *")
            if st.form_submit_button("💾 Add"):
                if etn:
                    db.table('expense_types').insert({
                        'name': etn, 'is_active': True
                    }).execute()
                    st.success("Added!")
                    time.sleep(0.5)
                    st.rerun()

    with tab3:
        with st.form("chg_pw"):
            cpw = st.text_input("Current Password", type="password")
            npw = st.text_input("New Password", type="password")
            cpw2 = st.text_input("Confirm Password", type="password")
            if st.form_submit_button("🔑 Change"):
                if not all([cpw, npw, cpw2]):
                    st.error("All fields required!")
                elif npw != cpw2:
                    st.error("Passwords don't match!")
                elif len(npw) < 6:
                    st.error("Min 6 characters!")
                else:
                    try:
                        user = db.table('users').select('*').eq(
                            'id', st.session_state['user_id']
                        ).execute()
                        if user.data and check_password(
                            cpw, user.data[0]['password_hash']
                        ):
                            db.table('users').update({
                                'password_hash': hash_password(npw)
                            }).eq('id', st.session_state['user_id']).execute()
                            st.success("✅ Changed!")
                        else:
                            st.error("Wrong current password!")
                    except Exception as e:
                        st.error(f"Error: {e}")


# ============================================================
# USER MANAGEMENT (Admin)
# ============================================================
def user_management_page():
    if st.session_state['role'] != 'admin':
        st.error("⛔ Admin only!")
        return

    db = get_db()
    st.markdown("""
        <div class="main-header"><h1>👤 User Management</h1></div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📋 Users", "➕ Add"])

    with tab1:
        try:
            users = db.table('users').select('*').order('username').execute()
            if users.data:
                for u in users.data:
                    c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
                    with c1: st.write(f"**{u['username']}**")
                    with c2: st.write(u.get('full_name', '-'))
                    with c3: st.write(u.get('role', '').upper())
                    with c4:
                        status = "✅" if u.get('is_active_user', True) else "❌"
                        st.write(status)
                        if (u['username'] != 'admin' and
                                u['id'] != st.session_state['user_id']):
                            if st.button("🔄", key=f"tu_{u['id']}"):
                                db.table('users').update({
                                    'is_active_user': not u.get(
                                        'is_active_user', True
                                    )
                                }).eq('id', u['id']).execute()
                                st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    with tab2:
        with st.form("add_user"):
            c1, c2 = st.columns(2)
            with c1:
                nu = st.text_input("Username *")
                np_val = st.text_input("Password *", type="password")
            with c2:
                nf = st.text_input("Full Name")
                nr = st.selectbox("Role", ['user', 'admin'])

            if st.form_submit_button("💾 Create", use_container_width=True):
                if not nu or not np_val:
                    st.error("Username & password required!")
                elif len(np_val) < 6:
                    st.error("Min 6 characters!")
                else:
                    try:
                        existing = db.table('users').select('id').eq(
                            'username', nu
                        ).execute()
                        if existing.data:
                            st.error("Username exists!")
                        else:
                            db.table('users').insert({
                                'username': nu,
                                'password_hash': hash_password(np_val),
                                'full_name': nf or None,
                                'role': nr,
                                'is_active_user': True
                            }).execute()
                            st.success("✅ Created!")
                            time.sleep(0.5)
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")


# ============================================================
# DELETED BILLS (Admin)
# ============================================================
def deleted_bills_page():
    if st.session_state['role'] != 'admin':
        st.error("⛔ Admin only!")
        return

    db = get_db()
    st.markdown("""
        <div class="main-header"><h1>🗑️ Deleted Bills</h1></div>
    """, unsafe_allow_html=True)

    try:
        bills = db.table('bills').select(
            '*, devotees(name), pooja_types(name)'
        ).eq('is_deleted', True).order('deleted_at', desc=True).execute()

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

                st.warning(
                    f"🧾 {b.get('bill_number', '')} | {name} | "
                    f"{pooja} | {format_currency(b.get('amount', 0))} | "
                    f"Reason: {b.get('delete_reason', '-')}"
                )

                if st.button("♻️ Restore", key=f"rb_{b['id']}"):
                    db.table('bills').update({
                        'is_deleted': False,
                        'deleted_by': None,
                        'deleted_at': None,
                        'delete_reason': None
                    }).eq('id', b['id']).execute()
                    st.success("Restored!")
                    time.sleep(0.5)
                    st.rerun()
        else:
            st.info("No deleted bills")
    except Exception as e:
        st.error(f"Error: {e}")


# ============================================================
# MAIN APP
# ============================================================
def main():
    init_session_state()
    apply_custom_css()

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
            'billing': billing_page,
            'expenses': expenses_page,
            'reports': reports_page,
            'samaya': samaya_page,
            'mandapam': mandapam_page,
            'daily_pooja': daily_pooja_page,
            'settings': settings_page,
            'users': user_management_page,
            'deleted_bills': deleted_bills_page,
        }

        page_func = page_map.get(page, dashboard_page)
        page_func()


if __name__ == "__main__":
    main()
