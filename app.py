import streamlit as st
import bcrypt
from datetime import datetime, date, timedelta
import traceback
import base64

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Temple Management System",
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
TEMPLE_FULL = f"{TEMPLE_NAME}, {TEMPLE_TRUST} - {TEMPLE_REG}, {TEMPLE_PLACE}, {TEMPLE_DISTRICT}"

NATCHATHIRAM_LIST = [
    'Ashwini', 'Bharani', 'Krittika', 'Rohini', 'Mrigashira', 'Ardra',
    'Punarvasu', 'Pushya', 'Ashlesha', 'Magha', 'Purva Phalguni',
    'Uttara Phalguni', 'Hasta', 'Chitra', 'Swati', 'Vishakha',
    'Anuradha', 'Jyeshtha', 'Mula', 'Purva Ashadha', 'Uttara Ashadha',
    'Shravana', 'Dhanishta', 'Shatabhisha', 'Purva Bhadrapada',
    'Uttara Bhadrapada', 'Revati'
]

RELATION_TYPES = [
    'Self', 'Spouse', 'Son', 'Daughter', 'Father', 'Mother',
    'Brother', 'Sister', 'Grandfather', 'Grandmother',
    'Father-in-law', 'Mother-in-law', 'Son-in-law', 'Daughter-in-law',
    'Uncle', 'Aunt', 'Nephew', 'Niece', 'Cousin', 'Other'
]


# ============================================================
# SUPABASE CONNECTION
# ============================================================
@st.cache_resource
def init_supabase():
    try:
        from supabase import create_client
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        return None


def get_db():
    db = init_supabase()
    if db is None:
        st.error("Database connection failed! Check Supabase credentials in Settings > Secrets")
        st.stop()
    return db


# ============================================================
# PASSWORD HELPERS
# ============================================================
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed):
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except:
        return False


# ============================================================
# DATE HELPERS
# ============================================================
def parse_date(date_str):
    if not date_str:
        return None
    try:
        if isinstance(date_str, date):
            return date_str
        return datetime.strptime(str(date_str)[:10], '%Y-%m-%d').date()
    except:
        return None

def fmt_date(date_str):
    d = parse_date(date_str)
    return d.strftime('%d/%m/%Y') if d else '-'


# ============================================================
# IMAGE HELPERS
# ============================================================
def get_amman_image():
    if 'amman_img_cache' in st.session_state and st.session_state['amman_img_cache']:
        return st.session_state['amman_img_cache']
    try:
        db = get_db()
        for ext in ['png', 'jpg', 'jpeg']:
            try:
                data = db.storage.from_('temple-images').download(f'amman.{ext}')
                if data:
                    mime = 'png' if ext == 'png' else 'jpeg'
                    b64 = base64.b64encode(data).decode()
                    result = f"data:image/{mime};base64,{b64}"
                    st.session_state['amman_img_cache'] = result
                    return result
            except:
                continue
    except:
        pass
    return None

def get_temple_bg():
    if 'temple_bg_cache' in st.session_state and st.session_state['temple_bg_cache']:
        return st.session_state['temple_bg_cache']
    try:
        db = get_db()
        for ext in ['jpg', 'jpeg', 'png']:
            try:
                data = db.storage.from_('temple-images').download(f'temple_bg.{ext}')
                if data:
                    mime = 'png' if ext == 'png' else 'jpeg'
                    b64 = base64.b64encode(data).decode()
                    result = f"data:image/{mime};base64,{b64}"
                    st.session_state['temple_bg_cache'] = result
                    return result
            except:
                continue
    except:
        pass
    return None


# ============================================================
# INIT DEFAULT DATA
# ============================================================
def init_defaults():
    try:
        db = get_db()
        r = db.table('users').select('id').eq('username', 'admin').execute()
        if not r.data:
            db.table('users').insert({
                'username': 'admin', 'password_hash': hash_password('admin123'),
                'full_name': 'Administrator', 'role': 'admin', 'is_active_user': True
            }).execute()

        r = db.table('pooja_type').select('id').limit(1).execute()
        if not r.data:
            db.table('pooja_type').insert([
                {'name': 'Abhishekam', 'amount': 100, 'is_active': True},
                {'name': 'Archanai', 'amount': 50, 'is_active': True},
                {'name': 'Sahasranamam', 'amount': 200, 'is_active': True},
                {'name': 'Thiruvilakku Pooja', 'amount': 150, 'is_active': True},
                {'name': 'Ganapathi Homam', 'amount': 500, 'is_active': True},
                {'name': 'Navagraha Pooja', 'amount': 300, 'is_active': True},
                {'name': 'Annadhanam', 'amount': 1000, 'is_active': True},
            ]).execute()

        r = db.table('expense_type').select('id').limit(1).execute()
        if not r.data:
            db.table('expense_type').insert([
                {'name': 'Flowers', 'is_active': True}, {'name': 'Oil', 'is_active': True},
                {'name': 'Camphor', 'is_active': True}, {'name': 'Electricity', 'is_active': True},
                {'name': 'Maintenance', 'is_active': True}, {'name': 'Salary', 'is_active': True},
                {'name': 'Others', 'is_active': True},
            ]).execute()

        r = db.table('daily_pooja').select('id').limit(1).execute()
        if not r.data:
            db.table('daily_pooja').insert([
                {'pooja_name': 'சுப்ரபாதம்', 'pooja_time': '5:30 AM', 'description': 'Morning prayer', 'is_active': True},
                {'pooja_name': 'காலை அபிஷேகம்', 'pooja_time': '6:00 AM', 'description': 'Morning bath', 'is_active': True},
                {'pooja_name': 'காலை பூஜை', 'pooja_time': '7:00 AM', 'description': 'Morning worship', 'is_active': True},
                {'pooja_name': 'உச்சிக்கால பூஜை', 'pooja_time': '12:00 PM', 'description': 'Noon', 'is_active': True},
                {'pooja_name': 'சாயரக்ஷை', 'pooja_time': '6:00 PM', 'description': 'Evening', 'is_active': True},
                {'pooja_name': 'அர்த்த ஜாம பூஜை', 'pooja_time': '8:00 PM', 'description': 'Night', 'is_active': True},
            ]).execute()
    except Exception as e:
        pass


# ============================================================
# CUSTOM CSS
# ============================================================
def apply_css():
    st.markdown("""
    <style>
        .stApp { background: linear-gradient(135deg, #FFF8DC 0%, #FFEFD5 50%, #FFE4B5 100%); }

        /* Force sidebar visible and styled */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #8B0000 0%, #B22222 50%, #DC143C 100%) !important;
            min-width: 280px !important;
            width: 280px !important;
        }
        section[data-testid="stSidebar"] > div:first-child {
            padding-top: 0rem !important;
        }

        .temple-hdr {
            background: linear-gradient(135deg, #8B0000, #DC143C);
            color: #FFD700; padding: 15px 25px; border-radius: 12px;
            text-align: center; margin-bottom: 20px;
            box-shadow: 0 4px 15px rgba(139,0,0,0.3);
        }
        .temple-hdr h2 { font-size: 1.4em; margin: 0; color: #FFD700; }
        .temple-hdr p { font-size: 0.82em; margin: 2px 0; color: #FFF8DC; opacity:0.9; }

        .stat-card {
            border-radius: 15px; padding: 20px; color: white;
            box-shadow: 0 5px 20px rgba(0,0,0,0.15); text-align: center;
        }
        .s-inc { background: linear-gradient(135deg, #228B22, #32CD32); }
        .s-exp { background: linear-gradient(135deg, #DC143C, #FF4500); }
        .s-dev { background: linear-gradient(135deg, #4169E1, #6495ED); }
        .s-bil { background: linear-gradient(135deg, #FF8C00, #FFD700); }
        .stat-card h3 { font-size: 1.8em; font-weight: 700; margin: 5px 0; }
        .stat-card p { font-size: 0.85em; opacity: 0.9; margin: 0; }

        .pooja-card {
            background: linear-gradient(135deg, #FFF8DC, #FFEFD5);
            border: 1px solid #FFD700; border-radius: 10px; padding: 12px 15px;
            margin-bottom: 8px; border-left: 4px solid #8B0000;
        }
        .bday-card {
            background: #FFF8DC; border-radius: 8px; padding: 10px 15px;
            margin-bottom: 8px; border-left: 3px solid #DC143C;
        }

        /* News ticker */
        .ticker-wrap {
            background: linear-gradient(90deg, #8B0000, #DC143C, #8B0000);
            border-radius: 10px; padding: 10px 15px; overflow: hidden;
            margin-bottom: 20px; white-space: nowrap;
        }
        .ticker-move {
            display: inline-block; animation: ticker 25s linear infinite;
            color: #FFD700; font-weight: 600; font-size: 0.95em;
        }
        @keyframes ticker {
            0% { transform: translateX(100%); }
            100% { transform: translateX(-100%); }
        }

        .amman-round {
            width: 100px; height: 100px; border-radius: 50%;
            border: 4px solid #FFD700; object-fit: cover;
            box-shadow: 0 0 25px rgba(255,215,0,0.5);
            display: block; margin: 0 auto 10px;
        }
        .amman-sm {
            width: 55px; height: 55px; border-radius: 50%;
            border: 3px solid #FFD700; object-fit: cover;
            box-shadow: 0 0 15px rgba(255,215,0,0.4);
            display: block; margin: 0 auto 8px;
        }

        .bill-hdr {
            text-align: center; border-bottom: 3px double #8B0000;
            padding-bottom: 15px; margin-bottom: 15px;
        }

        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)


# ============================================================
# SESSION STATE
# ============================================================
def init_session():
    for k, v in {'logged_in': False, 'user_id': None, 'username': None,
                  'full_name': None, 'role': None, 'page': 'Dashboard',
                  'edit_devotee_id': None, 'print_bill_id': None,
                  'amman_img_cache': None, 'temple_bg_cache': None}.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ============================================================
# LOGIN PAGE
# ============================================================
def login_page():
    amman_img = get_amman_image()
    temple_bg = get_temple_bg()

    if temple_bg:
        st.markdown(f"""
        <div style="position:fixed;top:0;left:0;width:100%;height:100%;
            background-image:url('{temple_bg}');background-size:cover;background-position:center;
            filter:brightness(0.3);z-index:-2;"></div>
        <div style="position:fixed;top:0;left:0;width:100%;height:100%;
            background:linear-gradient(135deg,rgba(139,0,0,0.6),rgba(220,20,60,0.5));z-index:-1;"></div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("""<div style="background:rgba(255,255,255,0.96);border-radius:20px;padding:30px;
            box-shadow:0 20px 60px rgba(0,0,0,0.3);text-align:center;">""", unsafe_allow_html=True)

        if amman_img:
            st.markdown(f'<img src="{amman_img}" class="amman-round">', unsafe_allow_html=True)
        else:
            st.markdown('<div style="width:100px;height:100px;border-radius:50%;border:4px solid #FFD700;display:flex;align-items:center;justify-content:center;font-size:3em;margin:0 auto 10px;background:#FFF8DC;box-shadow:0 0 25px rgba(255,215,0,0.5);">🙏</div>', unsafe_allow_html=True)

        st.markdown(f"""
            <h2 style="color:#8B0000;margin:5px 0;">{TEMPLE_NAME}</h2>
            <p style="color:#DC143C;font-weight:600;">{TEMPLE_TRUST} - {TEMPLE_REG}</p>
            <p style="color:#888;font-size:0.82em;">{TEMPLE_PLACE}, {TEMPLE_DISTRICT}</p>
            <hr style="border-color:#FFD700;margin:12px auto;width:60%;">
        </div>""", unsafe_allow_html=True)

        with st.form("login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("🕉️ Login", use_container_width=True):
                if username and password:
                    try:
                        db = get_db()
                        r = db.table('users').select('*').eq('username', username).eq('is_active_user', True).execute()
                        if r.data and check_password(password, r.data[0]['password_hash']):
                            u = r.data[0]
                            st.session_state.update({'logged_in': True, 'user_id': u['id'],
                                'username': u['username'], 'full_name': u.get('full_name') or u['username'],
                                'role': u['role'], 'page': 'Dashboard'})
                            st.rerun()
                        else:
                            st.error("Invalid credentials!")
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.warning("Enter username and password")


# ============================================================
# SIDEBAR WITH SELECTBOX NAVIGATION (ALWAYS VISIBLE)
# ============================================================
def show_sidebar():
    with st.sidebar:
        amman_img = get_amman_image()

        # Header
        if amman_img:
            st.markdown(f'<img src="{amman_img}" class="amman-sm">', unsafe_allow_html=True)
        else:
            st.markdown('<div style="text-align:center;font-size:2.5em;">🕉️</div>', unsafe_allow_html=True)

        st.markdown(f"""
        <div style="text-align:center;padding-bottom:10px;border-bottom:2px solid rgba(255,215,0,0.3);">
            <p style="color:#FFD700;font-size:0.85em;font-weight:700;margin:3px 0;">{TEMPLE_NAME}</p>
            <p style="color:rgba(255,215,0,0.7);font-size:0.68em;margin:2px 0;">{TEMPLE_TRUST}</p>
            <p style="color:rgba(255,215,0,0.6);font-size:0.62em;">{TEMPLE_PLACE}, {TEMPLE_DISTRICT}</p>
            <p style="color:#FFD700;font-size:0.78em;margin-top:5px;">
                👤 {st.session_state['full_name']}
                {'  🔑ADMIN' if st.session_state['role']=='admin' else ''}
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("")

        # NAVIGATION USING SELECTBOX - ALWAYS VISIBLE
        menu_list = [
            "🏠 Dashboard",
            "👥 Devotees",
            "🧾 Billing",
            "💰 Expenses",
            "📊 Reports",
            "───────────",
            "🎓 Samaya Vakuppu",
            "🏛️ Thirumana Mandapam",
            "🙏 Daily Pooja Schedule",
            "───────────",
            "⚙️ Settings",
            "🖼️ Temple Images",
        ]

        if st.session_state['role'] == 'admin':
            menu_list.extend([
                "───────────",
                "👤 User Management",
                "🗑️ Deleted Bills",
            ])

        # Get current page index
        current = st.session_state.get('page', 'Dashboard')
        try:
            current_idx = next(i for i, m in enumerate(menu_list) if current in m)
        except StopIteration:
            current_idx = 0

        st.markdown("<p style='color:#FFD700;font-weight:700;font-size:0.85em;'>📋 NAVIGATION</p>", unsafe_allow_html=True)

        selected = st.radio(
            "Menu",
            menu_list,
            index=current_idx,
            label_visibility="collapsed"
        )

        if selected and "──" not in selected:
            st.session_state['page'] = selected

        st.markdown("---")

        if st.button("🚪 LOGOUT", use_container_width=True, type="primary"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

        st.markdown(f"""
        <div style="text-align:center;padding-top:8px;font-size:0.68em;color:rgba(255,215,0,0.5);">
            📅 {datetime.now().strftime('%d %B %Y, %A')}
        </div>
        """, unsafe_allow_html=True)


# ============================================================
# NEWS TICKER
# ============================================================
def show_ticker(birthdays):
    msgs = [f"🎂 Happy Birthday {b['name']}!" for b in birthdays]
    if not msgs:
        msgs = [f"🕉️ Welcome to {TEMPLE_NAME} - {TEMPLE_TRUST} 🙏",
                "📞 For queries contact Temple Office",
                f"📍 {TEMPLE_PLACE}, {TEMPLE_DISTRICT}"]

    text = "     ⭐     ".join(msgs)
    st.markdown(f"""
    <div class="ticker-wrap">
        <div class="ticker-move">{text}     ⭐     {text}</div>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# DASHBOARD
# ============================================================
def pg_dashboard():
    db = get_db()
    amman_img = get_amman_image()
    today_d = date.today()

    # Find birthdays first for ticker
    birthdays = []
    try:
        all_dev = db.table('devotee').select('name, dob, mobile_no').eq('is_active', True).not_.is_('dob', 'null').execute()
        for d in (all_dev.data or []):
            dd = parse_date(d.get('dob'))
            if dd and dd.month == today_d.month and dd.day == today_d.day:
                birthdays.append(d)
    except:
        pass

    # NEWS TICKER
    show_ticker(birthdays)

    # Header
    amman_html = f'<img src="{amman_img}" style="width:65px;height:65px;border-radius:50%;border:3px solid #FFD700;object-fit:cover;">' if amman_img else '<span style="font-size:2.5em;">🕉️</span>'

    st.markdown(f"""
    <div class="temple-hdr">
        {amman_html}
        <h2>{TEMPLE_NAME}</h2>
        <p>{TEMPLE_TRUST} - {TEMPLE_REG}</p>
        <p>{TEMPLE_PLACE}, {TEMPLE_DISTRICT}</p>
    </div>
    """, unsafe_allow_html=True)

    # Period
    period = st.radio("📅 Period", ["Daily", "Weekly", "Monthly", "Yearly"], horizontal=True)

    if period == "Daily":
        sd, ed = today_d, today_d
    elif period == "Weekly":
        sd = today_d - timedelta(days=today_d.weekday())
        ed = today_d
    elif period == "Monthly":
        sd = today_d.replace(day=1)
        ed = today_d
    else:
        sd = today_d.replace(month=1, day=1)
        ed = today_d

    try:
        br = db.table('bill').select('amount').eq('is_deleted', False).gte('bill_date', sd.isoformat()).lte('bill_date', ed.isoformat()+'T23:59:59').execute()
        ti = sum(b['amount'] or 0 for b in (br.data or []))
        tb = len(br.data or [])
        er = db.table('expense').select('amount').gte('expense_date', sd.isoformat()).lte('expense_date', ed.isoformat()).execute()
        te = sum(e['amount'] or 0 for e in (er.data or []))
        dr = db.table('devotee').select('id', count='exact').eq('is_family_head', True).eq('is_active', True).execute()
        td = dr.count or 0
    except:
        ti = te = tb = td = 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="stat-card s-inc"><p>📈 {period} Income</p><h3>₹{ti:,.2f}</h3></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="stat-card s-exp"><p>📉 {period} Expenses</p><h3>₹{te:,.2f}</h3></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="stat-card s-dev"><p>👥 Devotees</p><h3>{td}</h3></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="stat-card s-bil"><p>🧾 {period} Bills</p><h3>{tb}</h3></div>', unsafe_allow_html=True)

    cl, cr = st.columns(2)
    with cl:
        st.markdown("### 🙏 Today's Pooja Schedule")
        try:
            dp = db.table('daily_pooja').select('*').eq('is_active', True).order('pooja_time').execute()
            for p in (dp.data or []):
                st.markdown(f"""<div class="pooja-card">
                    <strong style="color:#8B0000;">{p['pooja_name']}</strong> -
                    <span style="color:#8B0000;font-weight:700;">{p.get('pooja_time','TBD')}</span>
                    <br><small style="color:#666;">{p.get('description','')}</small>
                </div>""", unsafe_allow_html=True)
            if not dp.data:
                st.info("No pooja scheduled")
        except Exception as e:
            st.warning(str(e))

    with cr:
        st.markdown("### 🎂 Today's Birthdays")
        if birthdays:
            for b in birthdays:
                st.markdown(f'<div class="bday-card">🎂 <strong>{b["name"]}</strong> - {b.get("mobile_no","")}</div>', unsafe_allow_html=True)
        else:
            st.info("No birthdays today")

    # Recent bills
    st.markdown("### 🧾 Recent Bills")
    try:
        import pandas as pd
        rb = db.table('bill').select('bill_number, bill_date, amount, guest_name, devotee(name), pooja_type(name)').eq('is_deleted', False).order('bill_date', desc=True).limit(10).execute()
        if rb.data:
            rows = [{'Bill': b.get('bill_number','-'), 'Date': str(b.get('bill_date','-'))[:10],
                     'Name': (b.get('devotee') or {}).get('name','') or b.get('guest_name','-'),
                     'Pooja': (b.get('pooja_type') or {}).get('name','-'),
                     'Amount': f"₹{b.get('amount',0):,.2f}"} for b in rb.data]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("No bills yet")
    except Exception as e:
        st.warning(str(e))


# ============================================================
# DEVOTEES
# ============================================================
def pg_devotees():
    db = get_db()
    st.markdown("### 👥 Enrolled Devotees")

    c1, c2 = st.columns([3, 1])
    with c2:
        if st.button("➕ Add New Devotee", use_container_width=True, type="primary"):
            st.session_state['page'] = 'add_devotee'
            st.session_state['edit_devotee_id'] = None
            st.rerun()
    with c1:
        search = st.text_input("🔍 Search", placeholder="Name or mobile...")

    try:
        q = db.table('devotee').select('*').eq('is_family_head', True).eq('is_active', True).order('name')
        if search:
            q = q.ilike('name', f'%{search}%')
        result = q.execute()

        if result.data:
            for d in result.data:
                fm_r = db.table('devotee').select('id', count='exact').eq('family_head_id', d['id']).execute()
                fc = fm_r.count or 0

                with st.expander(f"**{d['name']}** | 📱 {d.get('mobile_no','-')} | ⭐ {d.get('natchathiram','-')} | 👨‍👩‍👧‍👦 {fc}"):
                    c1, c2, c3 = st.columns([2, 2, 1])
                    with c1:
                        st.write(f"**DOB:** {fmt_date(d.get('dob'))}")
                        st.write(f"**Mobile:** {d.get('mobile_no','-')}")
                        st.write(f"**WhatsApp:** {d.get('whatsapp_no','-')}")
                    with c2:
                        st.write(f"**Star:** {d.get('natchathiram','-')}")
                        st.write(f"**Wedding:** {fmt_date(d.get('wedding_day'))}")
                        st.write(f"**Address:** {d.get('address','-')}")
                    with c3:
                        if st.button("✏️ Edit", key=f"e{d['id']}"):
                            st.session_state['page'] = 'add_devotee'
                            st.session_state['edit_devotee_id'] = d['id']
                            st.rerun()
                        if st.button("🗑️ Delete", key=f"d{d['id']}"):
                            db.table('devotee_yearly_pooja').delete().eq('devotee_id', d['id']).execute()
                            db.table('devotee').delete().eq('family_head_id', d['id']).execute()
                            db.table('devotee').delete().eq('id', d['id']).execute()
                            st.success("Deleted!")
                            st.rerun()

                    # Family
                    import pandas as pd
                    fm = db.table('devotee').select('*').eq('family_head_id', d['id']).execute()
                    if fm.data:
                        st.markdown("**👨‍👩‍👧‍👦 Family:**")
                        st.dataframe(pd.DataFrame([{'Name': f['name'], 'Relation': f.get('relation_type','-'),
                            'DOB': fmt_date(f.get('dob')), 'Star': f.get('natchathiram','-'),
                            'Mobile': f.get('mobile_no','-')} for f in fm.data]), use_container_width=True, hide_index=True)
        else:
            st.info("No devotees found")
    except Exception as e:
        st.error(str(e))


# ============================================================
# ADD/EDIT DEVOTEE
# ============================================================
def pg_add_devotee():
    db = get_db()
    eid = st.session_state.get('edit_devotee_id')
    dd = None
    if eid:
        r = db.table('devotee').select('*').eq('id', eid).execute()
        dd = r.data[0] if r.data else None
        st.markdown(f"### ✏️ Edit Devotee #{eid}")
    else:
        st.markdown("### ➕ Add Devotee")

    if st.button("⬅️ Back"):
        st.session_state['page'] = '👥 Devotees'
        st.rerun()

    with st.form("devf"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Name *", value=dd.get('name','') if dd else '')
            dob = st.date_input("DOB", value=parse_date(dd.get('dob')) if dd else None)
            mobile = st.text_input("Mobile", value=dd.get('mobile_no','') if dd else '')
            ri = (RELATION_TYPES.index(dd['relation_type'])+1) if dd and dd.get('relation_type') in RELATION_TYPES else 0
            relation = st.selectbox("Relation", ['']+RELATION_TYPES, index=ri)
        with c2:
            whatsapp = st.text_input("WhatsApp", value=dd.get('whatsapp_no','') if dd else '')
            wedding = st.date_input("Wedding", value=parse_date(dd.get('wedding_day')) if dd else None)
            si = (NATCHATHIRAM_LIST.index(dd['natchathiram'])+1) if dd and dd.get('natchathiram') in NATCHATHIRAM_LIST else 0
            star = st.selectbox("Natchathiram", ['']+NATCHATHIRAM_LIST, index=si)
            address = st.text_area("Address", value=dd.get('address','') if dd else '')

        st.markdown("---")
        st.markdown("#### 👨‍👩‍👧‍👦 Family Members")
        efm = (db.table('devotee').select('*').eq('family_head_id', eid).execute().data or []) if eid else []
        nfm = st.number_input("Family count", 0, 15, len(efm))

        fam = []
        for i in range(int(nfm)):
            ef = efm[i] if i < len(efm) else {}
            f1, f2, f3, f4, f5 = st.columns(5)
            with f1: fn = st.text_input("Name", key=f"fn{i}", value=ef.get('name',''))
            with f2: fd = st.date_input("DOB", key=f"fd{i}", value=parse_date(ef.get('dob')))
            with f3:
                fri = (RELATION_TYPES.index(ef['relation_type'])+1) if ef.get('relation_type') in RELATION_TYPES else 0
                fr = st.selectbox("Rel", ['']+RELATION_TYPES, key=f"fr{i}", index=fri)
            with f4:
                fsi = (NATCHATHIRAM_LIST.index(ef['natchathiram'])+1) if ef.get('natchathiram') in NATCHATHIRAM_LIST else 0
                fs = st.selectbox("Star", ['']+NATCHATHIRAM_LIST, key=f"fs{i}", index=fsi)
            with f5: fm = st.text_input("Mobile", key=f"fm{i}", value=ef.get('mobile_no',''))
            if fn.strip():
                fam.append({'name':fn, 'dob':fd.isoformat() if fd else None, 'relation_type':fr or None,
                           'natchathiram':fs or None, 'mobile_no':fm or None})

        st.markdown("---")
        st.markdown("#### 🙏 Yearly Poojas")
        ptr = db.table('pooja_type').select('*').eq('is_active', True).execute()
        pts = ptr.data or []
        ptn = ['']+[p['name'] for p in pts]
        ptm = {p['name']:p['id'] for p in pts}

        eyp = (db.table('devotee_yearly_pooja').select('*, pooja_type(name)').eq('devotee_id', eid).execute().data or []) if eid else []
        nyp = st.number_input("Yearly pooja count", 0, 20, len(eyp))

        yps = []
        for i in range(int(nyp)):
            ey = eyp[i] if i < len(eyp) else {}
            epn = (ey.get('pooja_type') or {}).get('name','')
            y1, y2, y3 = st.columns(3)
            with y1:
                yi = ptn.index(epn) if epn in ptn else 0
                yt = st.selectbox(f"Pooja {i+1}", ptn, key=f"yt{i}", index=yi)
            with y2: yd = st.date_input(f"Date {i+1}", key=f"yd{i}", value=parse_date(ey.get('pooja_date')))
            with y3: yn = st.text_input(f"Notes {i+1}", key=f"yn{i}", value=ey.get('notes',''))
            if yt:
                yps.append({'pooja_type_id':ptm.get(yt), 'pooja_name':yt,
                           'pooja_date':yd.isoformat() if yd else None, 'notes':yn or None})

        if st.form_submit_button("💾 Save", use_container_width=True):
            if not name.strip():
                st.error("Name required!")
            else:
                rec = {'name':name.strip(), 'dob':dob.isoformat() if dob else None,
                       'relation_type':relation or None, 'mobile_no':mobile or None,
                       'whatsapp_no':whatsapp or None, 'wedding_day':wedding.isoformat() if wedding else None,
                       'natchathiram':star or None, 'address':address or None,
                       'is_family_head':True, 'is_active':True}
                try:
                    if eid:
                        db.table('devotee').update(rec).eq('id', eid).execute()
                        did = eid
                        db.table('devotee').delete().eq('family_head_id', eid).execute()
                        db.table('devotee_yearly_pooja').delete().eq('devotee_id', eid).execute()
                    else:
                        r = db.table('devotee').insert(rec).execute()
                        did = r.data[0]['id']

                    for f in fam:
                        db.table('devotee').insert({**f, 'is_family_head':False, 'family_head_id':did,
                            'address':address or None, 'is_active':True}).execute()
                    for y in yps:
                        db.table('devotee_yearly_pooja').insert({**y, 'devotee_id':did}).execute()

                    st.success("✅ Saved!")
                    st.session_state['page'] = '👥 Devotees'
                    st.session_state['edit_devotee_id'] = None
                    st.rerun()
                except Exception as e:
                    st.error(str(e))


# ============================================================
# BILLING
# ============================================================
def pg_billing():
    db = get_db()
    st.markdown("### 🧾 Bills")

    c1, c2 = st.columns([3, 1])
    with c2:
        if st.button("➕ New Bill", use_container_width=True, type="primary"):
            st.session_state['page'] = 'new_bill'
            st.rerun()

    f1, f2 = st.columns(2)
    with f1: fd = st.date_input("From", value=date.today(), key="bf")
    with f2: td = st.date_input("To", value=date.today(), key="bt")

    try:
        bills = db.table('bill').select('*, devotee(name), pooja_type(name)').gte('bill_date', fd.isoformat()).lte('bill_date', td.isoformat()+'T23:59:59').order('bill_date', desc=True).execute()
        total = 0
        if bills.data:
            for b in bills.data:
                dl = b.get('is_deleted', False)
                nm = (b.get('devotee') or {}).get('name','') or b.get('guest_name','-')
                pj = (b.get('pooja_type') or {}).get('name','-')
                am = b.get('amount',0) or 0
                if not dl: total += am

                with st.expander(f"{'🗑️' if dl else '✅'} {b.get('bill_number','-')} | {nm} | {pj} | ₹{am:,.2f}"):
                    st.write(f"**Bill:** {b.get('bill_number','-')} | **Manual:** {b.get('manual_bill_no','-')} | **Date:** {str(b.get('bill_date','-'))[:16]}")
                    st.write(f"**Name:** {nm} | **Pooja:** {pj} | **Amount:** ₹{am:,.2f} | **Notes:** {b.get('notes','-')}")
                    if not dl:
                        bc1, bc2 = st.columns(2)
                        with bc1:
                            if st.button("🖨️ Print", key=f"p{b['id']}"):
                                st.session_state['print_bill_id'] = b['id']
                                st.session_state['page'] = 'view_bill'
                                st.rerun()
                        with bc2:
                            if st.session_state['role'] == 'admin':
                                rs = st.text_input("Reason", key=f"r{b['id']}")
                                if st.button("🗑️ Delete", key=f"x{b['id']}"):
                                    if rs.strip():
                                        db.table('bill').update({'is_deleted':True, 'deleted_by':st.session_state['user_id'],
                                            'deleted_at':datetime.now().isoformat(), 'delete_reason':rs}).eq('id', b['id']).execute()
                                        st.rerun()
                                    else:
                                        st.warning("Enter reason!")
            st.markdown(f"**Total Active: ₹{total:,.2f}**")
        else:
            st.info("No bills found")
    except Exception as e:
        st.error(str(e))


def pg_new_bill():
    db = get_db()
    st.markdown("### 🧾 New Bill")
    if st.button("⬅️ Back"):
        st.session_state['page'] = '🧾 Billing'
        st.rerun()

    try:
        lb = db.table('bill').select('id').order('id', desc=True).limit(1).execute()
        nid = (lb.data[0]['id']+1) if lb.data else 1
    except:
        nid = 1
    nno = f"BILL-{nid:06d}"

    with st.form("bf"):
        c1, c2, c3 = st.columns(3)
        with c1: bn = st.text_input("Bill No", value=nno, disabled=True)
        with c2: mn = st.text_input("Manual No")
        with c3: bk = st.text_input("Book No")

        bd = st.date_input("Date", value=date.today())
        dt = st.radio("Type", ["Enrolled", "Guest"], horizontal=True)

        did = None; gn = ga = gm = gw = None
        if dt == "Enrolled":
            devs = db.table('devotee').select('id,name,mobile_no,address').eq('is_family_head',True).eq('is_active',True).order('name').execute()
            if devs.data:
                opts = {f"{d['name']} (ID:{d['id']})":d for d in devs.data}
                sel = st.selectbox("Devotee *", ['']+list(opts.keys()))
                if sel:
                    did = opts[sel]['id']
                    st.info(f"📱 {opts[sel].get('mobile_no','-')} | 📍 {opts[sel].get('address','-')}")
        else:
            g1, g2 = st.columns(2)
            with g1: gn = st.text_input("Guest Name *"); gm = st.text_input("Mobile")
            with g2: ga = st.text_area("Address", height=68); gw = st.text_input("WhatsApp")

        pts = db.table('pooja_type').select('*').eq('is_active', True).execute()
        pto = {f"{p['name']} (₹{p['amount']})":p for p in (pts.data or [])}
        sp = st.selectbox("Pooja *", ['']+list(pto.keys()))
        da = pto[sp]['amount'] if sp else 0
        amt = st.number_input("Amount *", min_value=0.0, value=float(da), step=1.0)
        notes = st.text_input("Notes")

        if st.form_submit_button("💾 Create Bill", use_container_width=True):
            if dt=="Enrolled" and not did: st.error("Select devotee!")
            elif dt=="Guest" and not (gn and gn.strip()): st.error("Enter guest name!")
            elif not sp: st.error("Select pooja!")
            elif amt <= 0: st.error("Amount > 0!")
            else:
                try:
                    r = db.table('bill').insert({
                        'bill_number':nno, 'manual_bill_no':mn or None, 'bill_book_no':bk or None,
                        'bill_date':bd.isoformat()+'T'+datetime.now().strftime('%H:%M:%S'),
                        'devotee_type':'enrolled' if dt=="Enrolled" else 'guest',
                        'devotee_id':did if dt=="Enrolled" else None,
                        'guest_name':gn if dt=="Guest" else None,
                        'guest_address':ga if dt=="Guest" else None,
                        'guest_mobile':gm if dt=="Guest" else None,
                        'guest_whatsapp':gw if dt=="Guest" else None,
                        'pooja_type_id':pto[sp]['id'], 'amount':amt, 'notes':notes or None,
                        'created_by':st.session_state['user_id'], 'is_deleted':False
                    }).execute()
                    st.success(f"✅ {nno} created!")
                    st.session_state['print_bill_id'] = r.data[0]['id']
                    st.session_state['page'] = 'view_bill'
                    st.rerun()
                except Exception as e:
                    st.error(str(e))


def pg_view_bill():
    db = get_db()
    bid = st.session_state.get('print_bill_id')
    if not bid:
        st.session_state['page'] = '🧾 Billing'; st.rerun(); return

    if st.button("⬅️ Back"):
        st.session_state['page'] = '🧾 Billing'; st.rerun()

    try:
        r = db.table('bill').select('*, devotee(name,mobile_no,address), pooja_type(name)').eq('id', bid).execute()
        if not r.data: st.error("Not found!"); return
        b = r.data[0]
        nm = (b.get('devotee') or {}).get('name','') or b.get('guest_name','-')
        mb = (b.get('devotee') or {}).get('mobile_no','') or b.get('guest_mobile','-')
        ad = (b.get('devotee') or {}).get('address','') or b.get('guest_address','-')
        pj = (b.get('pooja_type') or {}).get('name','-')
        am = b.get('amount',0)
        ai = get_amman_image()
        ah = f'<img src="{ai}" style="width:50px;height:50px;border-radius:50%;border:2px solid #FFD700;object-fit:cover;">' if ai else '🕉️'

        st.markdown(f"""
        <div style="background:white;padding:30px;border-radius:12px;box-shadow:0 2px 15px rgba(0,0,0,0.1);max-width:700px;margin:auto;">
            <div style="text-align:center;border-bottom:3px double #8B0000;padding-bottom:15px;margin-bottom:15px;">
                <div style="display:flex;align-items:center;justify-content:center;gap:15px;">
                    {ah}<div><h2 style="color:#8B0000;margin:0;font-size:1.2em;">{TEMPLE_NAME}</h2>
                    <p style="color:#DC143C;margin:2px 0;font-size:0.85em;">{TEMPLE_TRUST} - {TEMPLE_REG}</p></div>{ah}
                </div>
                <p style="color:#555;font-size:0.78em;">{TEMPLE_PLACE}, {TEMPLE_DISTRICT}</p>
                <p style="font-weight:700;color:#8B0000;margin-top:5px;">BILL RECEIPT</p>
            </div>
            <table style="width:100%;font-size:0.88em;"><tr><td><b>Bill:</b> {b.get('bill_number','-')}</td><td><b>Manual:</b> {b.get('manual_bill_no','-')}</td></tr>
            <tr><td><b>Date:</b> {str(b.get('bill_date','-'))[:16]}</td><td><b>Book:</b> {b.get('bill_book_no','-')}</td></tr></table>
            <hr style="border-color:#FFD700;"><p><b>Name:</b> {nm} | <b>Mobile:</b> {mb}</p><p><b>Address:</b> {ad}</p><hr style="border-color:#FFD700;">
            <table style="width:100%;border-collapse:collapse;margin:10px 0;">
            <thead><tr style="background:linear-gradient(135deg,#8B0000,#DC143C);color:white;"><th style="padding:8px;text-align:left;">Pooja</th><th style="padding:8px;">Notes</th><th style="padding:8px;text-align:right;">Amount</th></tr></thead>
            <tbody><tr><td style="padding:8px;border:1px solid #ddd;">{pj}</td><td style="padding:8px;border:1px solid #ddd;">{b.get('notes','-')}</td><td style="padding:8px;text-align:right;border:1px solid #ddd;">₹{am:,.2f}</td></tr></tbody>
            <tfoot><tr><td colspan="2" style="padding:8px;text-align:right;"><b>Total:</b></td><td style="padding:8px;text-align:right;color:#8B0000;font-size:1.2em;"><b>₹{am:,.2f}</b></td></tr></tfoot></table>
            <div style="text-align:center;margin-top:12px;padding-top:8px;border-top:1px dashed #ccc;"><small style="color:#888;">{TEMPLE_FULL}<br>🕉️ Thank you 🙏</small></div>
        </div>""", unsafe_allow_html=True)
        st.info("📌 Press Ctrl+P to print")
    except Exception as e:
        st.error(str(e))


# ============================================================
# EXPENSES
# ============================================================
def pg_expenses():
    db = get_db()
    st.markdown("### 💰 Expenses")
    f1, f2 = st.columns(2)
    with f1: fd = st.date_input("From", value=date.today().replace(day=1), key="ef")
    with f2: td = st.date_input("To", value=date.today(), key="et")

    with st.expander("➕ Add Expense"):
        ets = db.table('expense_type').select('*').eq('is_active', True).execute()
        eto = {e['name']:e['id'] for e in (ets.data or [])}
        with st.form("ef"):
            e1, e2, e3 = st.columns(3)
            with e1: et = st.selectbox("Type *", list(eto.keys()) if eto else [])
            with e2: ea = st.number_input("Amount *", min_value=0.01, step=1.0)
            with e3: ed = st.date_input("Date", value=date.today(), key="ned")
            edesc = st.text_area("Description", height=68)
            if st.form_submit_button("💾 Save"):
                if et and ea > 0:
                    db.table('expense').insert({'expense_type_id':eto[et], 'amount':ea,
                        'description':edesc or None, 'expense_date':ed.isoformat(),
                        'created_by':st.session_state['user_id']}).execute()
                    st.success("✅ Added!"); st.rerun()

    try:
        import pandas as pd
        exps = db.table('expense').select('*, expense_type(name)').gte('expense_date', fd.isoformat()).lte('expense_date', td.isoformat()).order('expense_date', desc=True).execute()
        if exps.data:
            tot = sum(e.get('amount',0) or 0 for e in exps.data)
            st.dataframe(pd.DataFrame([{'ID':e['id'], 'Date':e.get('expense_date','-'),
                'Type':(e.get('expense_type') or {}).get('name','-'),
                'Desc':e.get('description','-'), 'Amount':f"₹{e.get('amount',0):,.2f}"} for e in exps.data]),
                use_container_width=True, hide_index=True)
            st.markdown(f"**Total: ₹{tot:,.2f}**")
            di = st.number_input("ID to delete", min_value=0, step=1, key="edel")
            if st.button("🗑️ Delete") and di > 0:
                db.table('expense').delete().eq('id', int(di)).execute(); st.rerun()
        else:
            st.info("No expenses")
    except Exception as e:
        st.error(str(e))


# ============================================================
# REPORTS
# ============================================================
def pg_reports():
    db = get_db()
    st.markdown("### 📊 Reports")
    c1, c2 = st.columns(2)
    with c1: fd = st.date_input("From", value=date.today().replace(day=1), key="rf")
    with c2: td = st.date_input("To", value=date.today(), key="rt")

    try:
        from collections import defaultdict
        import pandas as pd
        bs = db.table('bill').select('amount, pooja_type(name)').eq('is_deleted', False).gte('bill_date', fd.isoformat()).lte('bill_date', td.isoformat()+'T23:59:59').execute()
        inc = sum(b['amount'] or 0 for b in (bs.data or []))
        es = db.table('expense').select('amount, expense_type(name)').gte('expense_date', fd.isoformat()).lte('expense_date', td.isoformat()).execute()
        exp = sum(e['amount'] or 0 for e in (es.data or []))

        c1, c2, c3 = st.columns(3)
        with c1: st.markdown(f'<div class="stat-card s-inc"><p>📈 Income</p><h3>₹{inc:,.2f}</h3></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="stat-card s-exp"><p>📉 Expenses</p><h3>₹{exp:,.2f}</h3></div>', unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="stat-card" style="background:linear-gradient(135deg,#4B0082,#8A2BE2);"><p>💰 Net</p><h3>₹{inc-exp:,.2f}</h3></div>', unsafe_allow_html=True)

        l, r = st.columns(2)
        with l:
            st.markdown("#### Income by Pooja")
            pi = defaultdict(lambda:{'c':0,'t':0})
            for b in (bs.data or []):
                n = (b.get('pooja_type') or {}).get('name','Other')
                pi[n]['c'] += 1; pi[n]['t'] += b['amount'] or 0
            if pi: st.dataframe(pd.DataFrame([{'Pooja':k,'Count':v['c'],'Amount':f"₹{v['t']:,.2f}"} for k,v in pi.items()]), use_container_width=True, hide_index=True)
        with r:
            st.markdown("#### Expenses by Type")
            pe = defaultdict(lambda:{'c':0,'t':0})
            for e in (es.data or []):
                n = (e.get('expense_type') or {}).get('name','Other')
                pe[n]['c'] += 1; pe[n]['t'] += e['amount'] or 0
            if pe: st.dataframe(pd.DataFrame([{'Type':k,'Count':v['c'],'Amount':f"₹{v['t']:,.2f}"} for k,v in pe.items()]), use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(str(e))


# ============================================================
# SAMAYA VAKUPPU
# ============================================================
def pg_samaya():
    db = get_db()
    st.markdown("### 🎓 Samaya Vakuppu")
    with st.expander("➕ Add"):
        with st.form("sf"):
            s1, s2 = st.columns(2)
            with s1: sn=st.text_input("Name *"); sd=st.date_input("DOB",value=None,key="sd"); sf=st.text_input("Father/Mother"); sb=st.text_input("Bank")
            with s2: sbn=st.text_input("Bond No"); sbd=st.date_input("Bond Date",value=None,key="sbd"); sbr=st.text_input("Branch"); sa=st.text_area("Address",height=68)
            if st.form_submit_button("💾"):
                if sn.strip():
                    db.table('samaya_vakuppu').insert({'student_name':sn,'dob':sd.isoformat() if sd else None,
                        'father_mother_name':sf or None,'bond_no':sbn or None,'bond_issue_date':sbd.isoformat() if sbd else None,
                        'bond_issuing_bank':sb or None,'branch_of_bank':sbr or None,'address':sa or None}).execute()
                    st.success("✅"); st.rerun()
    try:
        import pandas as pd
        ss = db.table('samaya_vakuppu').select('*').order('student_name').execute()
        if ss.data:
            st.dataframe(pd.DataFrame([{'ID':s['id'],'Name':s['student_name'],'DOB':fmt_date(s.get('dob')),
                'Father':s.get('father_mother_name','-'),'Bond':s.get('bond_no','-')} for s in ss.data]), use_container_width=True, hide_index=True)
            di = st.number_input("ID to delete", min_value=0, step=1, key="sdel")
            if st.button("🗑️") and di>0: db.table('samaya_vakuppu').delete().eq('id',int(di)).execute(); st.rerun()
    except Exception as e: st.error(str(e))


# ============================================================
# MANDAPAM
# ============================================================
def pg_mandapam():
    db = get_db()
    st.markdown("### 🏛️ Thirumana Mandapam")
    with st.expander("➕ Add"):
        with st.form("mf"):
            m1, m2 = st.columns(2)
            with m1: mn=st.text_input("Name *"); mbn=st.text_input("Bond No"); mbd=st.date_input("Date",value=None,key="mbd")
            with m2: ma=st.number_input("Amount",min_value=0.0,step=1.0); mnb=st.number_input("Bonds",min_value=1,value=1); mad=st.text_area("Address",height=68)
            if st.form_submit_button("💾"):
                if mn.strip():
                    db.table('thirumana_mandapam').insert({'name':mn,'bond_no':mbn or None,
                        'bond_issued_date':mbd.isoformat() if mbd else None,'amount':ma,'no_of_bond':mnb,'address':mad or None}).execute()
                    st.success("✅"); st.rerun()
    try:
        import pandas as pd
        ms = db.table('thirumana_mandapam').select('*').order('name').execute()
        if ms.data:
            st.dataframe(pd.DataFrame([{'ID':m['id'],'Name':m['name'],'Bond':m.get('bond_no','-'),
                'Amount':f"₹{m.get('amount',0):,.2f}",'Bonds':m.get('no_of_bond',1)} for m in ms.data]), use_container_width=True, hide_index=True)
            di = st.number_input("ID to delete", min_value=0, step=1, key="mdel")
            if st.button("🗑️") and di>0: db.table('thirumana_mandapam').delete().eq('id',int(di)).execute(); st.rerun()
    except Exception as e: st.error(str(e))


# ============================================================
# DAILY POOJA
# ============================================================
def pg_daily_pooja():
    db = get_db()
    st.markdown("### 🙏 Daily Pooja Schedule")
    with st.expander("➕ Add"):
        with st.form("dpf"):
            dpn=st.text_input("Name *"); dpt=st.text_input("Time (e.g. 6:00 AM)"); dpd=st.text_input("Description")
            if st.form_submit_button("💾"):
                if dpn.strip():
                    db.table('daily_pooja').insert({'pooja_name':dpn,'pooja_time':dpt or None,'description':dpd or None,'is_active':True}).execute()
                    st.success("✅"); st.rerun()
    try:
        ps = db.table('daily_pooja').select('*').eq('is_active', True).order('pooja_time').execute()
        for p in (ps.data or []):
            c1, c2 = st.columns([4,1])
            with c1:
                st.markdown(f"""<div class="pooja-card"><strong style="color:#8B0000;">{p['pooja_name']}</strong> - <span style="color:#8B0000;font-weight:700;">{p.get('pooja_time','TBD')}</span><br><small style="color:#666;">{p.get('description','')}</small></div>""", unsafe_allow_html=True)
            with c2:
                if st.button("🗑️", key=f"dp{p['id']}"):
                    db.table('daily_pooja').update({'is_active':False}).eq('id',p['id']).execute(); st.rerun()
    except Exception as e: st.error(str(e))


# ============================================================
# SETTINGS
# ============================================================
def pg_settings():
    db = get_db()
    st.markdown("### ⚙️ Settings")
    cl, cr = st.columns(2)
    with cl:
        st.markdown("#### 🙏 Pooja Types")
        with st.form("ptf"):
            pn=st.text_input("Name *",key="pn"); pa=st.number_input("Amount",min_value=0.0,step=1.0,key="pa")
            if st.form_submit_button("➕ Add"):
                if pn.strip(): db.table('pooja_type').insert({'name':pn,'amount':pa,'is_active':True}).execute(); st.rerun()
        pts = db.table('pooja_type').select('*').eq('is_active', True).execute()
        for p in (pts.data or []):
            pc1, pc2, pc3 = st.columns([3,1,1])
            with pc1: st.write(f"**{p['name']}**")
            with pc2: st.write(f"₹{p['amount']}")
            with pc3:
                if st.button("🗑️",key=f"pt{p['id']}"): db.table('pooja_type').update({'is_active':False}).eq('id',p['id']).execute(); st.rerun()
    with cr:
        st.markdown("#### 💰 Expense Types")
        with st.form("etf"):
            en=st.text_input("Name *",key="en")
            if st.form_submit_button("➕ Add"):
                if en.strip(): db.table('expense_type').insert({'name':en,'is_active':True}).execute(); st.rerun()
        ets = db.table('expense_type').select('*').eq('is_active', True).execute()
        for e in (ets.data or []):
            ec1, ec2 = st.columns([4,1])
            with ec1: st.write(f"**{e['name']}**")
            with ec2:
                if st.button("🗑️",key=f"et{e['id']}"): db.table('expense_type').update({'is_active':False}).eq('id',e['id']).execute(); st.rerun()


# ============================================================
# TEMPLE IMAGES
# ============================================================
def pg_images():
    st.markdown("### 🖼️ Temple Images")
    st.markdown("Upload **Amman image** (round icon) and **Temple background** (login page)")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 🙏 Amman Image")
        ai = get_amman_image()
        if ai:
            st.markdown(f'<img src="{ai}" class="amman-round">', unsafe_allow_html=True)
            st.success("✅ Image set")
        else:
            st.info("No image. Using default 🙏")

        af = st.file_uploader("Upload Amman image", type=['png','jpg','jpeg'], key="au")
        if af and st.button("📤 Upload Amman", key="ub1"):
            try:
                db = get_db()
                ext = af.name.rsplit('.',1)[-1].lower()
                for e in ['png','jpg','jpeg']:
                    try: db.storage.from_('temple-images').remove([f'amman.{e}'])
                    except: pass
                db.storage.from_('temple-images').upload(f'amman.{ext}', af.read())
                st.session_state['amman_img_cache'] = None
                st.success("✅ Uploaded!"); st.rerun()
            except Exception as e:
                st.error(str(e))

    with c2:
        st.markdown("#### 🏛️ Temple Background")
        bg = get_temple_bg()
        if bg:
            st.markdown(f'<img src="{bg}" style="width:250px;height:150px;border-radius:10px;object-fit:cover;border:2px solid #FFD700;">', unsafe_allow_html=True)
            st.success("✅ Background set")
        else:
            st.info("No background uploaded")

        bf = st.file_uploader("Upload background", type=['png','jpg','jpeg'], key="bu")
        if bf and st.button("📤 Upload Background", key="ub2"):
            try:
                db = get_db()
                ext = bf.name.rsplit('.',1)[-1].lower()
                for e in ['png','jpg','jpeg']:
                    try: db.storage.from_('temple-images').remove([f'temple_bg.{e}'])
                    except: pass
                db.storage.from_('temple-images').upload(f'temple_bg.{ext}', bf.read())
                st.session_state['temple_bg_cache'] = None
                st.success("✅ Uploaded!"); st.rerun()
            except Exception as e:
                st.error(str(e))

    if st.button("🔄 Refresh Images"):
        st.session_state['amman_img_cache'] = None
        st.session_state['temple_bg_cache'] = None
        st.rerun()


# ============================================================
# USER MANAGEMENT
# ============================================================
def pg_users():
    db = get_db()
    if st.session_state['role'] != 'admin': st.error("Admin only!"); return
    st.markdown("### 👤 Users")
    with st.expander("➕ Add User"):
        with st.form("uf"):
            un=st.text_input("Username *"); ufn=st.text_input("Full Name"); up=st.text_input("Password *",type="password"); ur=st.selectbox("Role",["user","admin"])
            if st.form_submit_button("💾"):
                if un.strip() and up:
                    ex = db.table('users').select('id').eq('username',un).execute()
                    if ex.data: st.error("Exists!")
                    else:
                        db.table('users').insert({'username':un,'password_hash':hash_password(up),'full_name':ufn or None,'role':ur,'is_active_user':True}).execute()
                        st.success("✅"); st.rerun()
    users = db.table('users').select('*').execute()
    for u in (users.data or []):
        c1,c2,c3 = st.columns([3,2,1])
        with c1: st.write(f"**{u['username']}** ({u.get('full_name','-')})")
        with c2: st.write(f"{'🔑Admin' if u['role']=='admin' else '👤User'} {'✅' if u['is_active_user'] else '❌'}")
        with c3:
            if u['id'] != st.session_state['user_id']:
                if st.button("Toggle",key=f"ut{u['id']}"):
                    db.table('users').update({'is_active_user':not u['is_active_user']}).eq('id',u['id']).execute(); st.rerun()


def pg_deleted_bills():
    db = get_db()
    if st.session_state['role'] != 'admin': st.error("Admin only!"); return
    st.markdown("### 🗑️ Deleted Bills")
    import pandas as pd
    bills = db.table('bill').select('*, devotee(name), pooja_type(name)').eq('is_deleted', True).order('deleted_at', desc=True).execute()
    ur = db.table('users').select('id,username,full_name').execute()
    um = {u['id']:u.get('full_name') or u['username'] for u in (ur.data or [])}
    if bills.data:
        st.dataframe(pd.DataFrame([{'Bill':b.get('bill_number','-'),'Date':str(b.get('bill_date','-'))[:10],
            'Name':(b.get('devotee') or {}).get('name','') or b.get('guest_name','-'),
            'Amount':f"₹{b.get('amount',0):,.2f}",'By':um.get(b.get('deleted_by'),'-'),
            'When':str(b.get('deleted_at','-'))[:16],'Reason':b.get('delete_reason','-')} for b in bills.data]),
            use_container_width=True, hide_index=True)
    else: st.info("No deleted bills")


# ============================================================
# MAIN
# ============================================================
def main():
    init_session()
    apply_css()

    try:
        init_defaults()
    except:
        pass

    if not st.session_state['logged_in']:
        login_page()
        return

    show_sidebar()

    # Route pages
    page = st.session_state.get('page', 'Dashboard')

    if 'Dashboard' in page:
        pg_dashboard()
    elif 'Devotees' in page:
        pg_devotees()
    elif page == 'add_devotee':
        pg_add_devotee()
    elif 'Billing' in page:
        pg_billing()
    elif page == 'new_bill':
        pg_new_bill()
    elif page == 'view_bill':
        pg_view_bill()
    elif 'Expenses' in page:
        pg_expenses()
    elif 'Reports' in page:
        pg_reports()
    elif 'Samaya' in page:
        pg_samaya()
    elif 'Mandapam' in page or 'Thirumana' in page:
        pg_mandapam()
    elif 'Daily Pooja' in page:
        pg_daily_pooja()
    elif 'Settings' in page:
        pg_settings()
    elif 'Images' in page:
        pg_images()
    elif 'User' in page:
        pg_users()
    elif 'Deleted' in page:
        pg_deleted_bills()
    else:
        pg_dashboard()


if __name__ == "__main__":
    main()
