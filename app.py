import streamlit as st
import httpx
import json
import io
import base64
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

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
# TEMPLE CONFIG
# ============================================================
TEMPLE_NAME = "Arulmigu Bhadreshwari Amman Kovil"
TEMPLE_TRUST = "Samrakshana Seva Trust"
TEMPLE_REG = "179/2004"
TEMPLE_PLACE = "Kanjampuram"
TEMPLE_DISTRICT = "Kanniyakumari Dist- 629154"
TEMPLE_ADDRESS_LINE2 = f"{TEMPLE_TRUST} - {TEMPLE_REG}"
TEMPLE_ADDRESS_LINE3 = f"{TEMPLE_PLACE}, {TEMPLE_DISTRICT}"
TEMPLE_FULL_ADDRESS = f"{TEMPLE_NAME}, {TEMPLE_ADDRESS_LINE2}, {TEMPLE_ADDRESS_LINE3}"

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

ASSET_CONDITIONS = ['New', 'Good', 'Fair', 'Poor', 'Damaged', 'Under Repair', 'Disposed']

ASSET_DEFAULT_CATEGORIES = [
    'Furniture', 'Vessels & Utensils', 'Electronics', 'Jewelry & Ornaments',
    'Vehicles', 'Musical Instruments', 'Pooja Items', 'Lighting & Electrical',
    'Textile & Decorations', 'Books & Scriptures', 'Kitchen Equipment',
    'Office Equipment', 'Processional Items', 'Statues & Idols',
    'Garden & Outdoor', 'Security Equipment', 'Other'
]


# ============================================================
# DATABASE - SUPABASE REST API
# ============================================================
def get_headers():
    key = st.secrets["supabase"]["key"]
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }


def get_url():
    return st.secrets["supabase"]["url"] + "/rest/v1"


def db_select(table, columns="*", filters=None, order=None, limit=None):
    try:
        url = f"{get_url()}/{table}?select={columns}"
        if filters:
            for key, value in filters.items():
                if isinstance(value, bool):
                    url += f"&{key}=eq.{str(value).lower()}"
                elif isinstance(value, dict):
                    for op, val in value.items():
                        url += f"&{key}={op}.{val}"
                else:
                    url += f"&{key}=eq.{value}"
        if order:
            if order.startswith('-'):
                url += f"&order={order[1:]}.desc"
            else:
                url += f"&order={order}.asc"
        if limit:
            url += f"&limit={limit}"
        response = httpx.get(url, headers=get_headers(), timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"DB Read Error: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        st.error(f"DB Error: {e}")
        return []


def db_insert(table, data):
    try:
        url = f"{get_url()}/{table}"
        response = httpx.post(url, headers=get_headers(), json=data, timeout=30)
        if response.status_code in [200, 201]:
            result = response.json()
            return result[0] if result else None
        else:
            st.error(f"DB Insert Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Insert Error: {e}")
        return None


def db_update(table, data, match_column, match_value):
    try:
        url = f"{get_url()}/{table}?{match_column}=eq.{match_value}"
        response = httpx.patch(url, headers=get_headers(), json=data, timeout=30)
        if response.status_code in [200, 204]:
            return True
        else:
            st.error(f"DB Update Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Update Error: {e}")
        return None


def db_delete(table, match_column, match_value):
    try:
        url = f"{get_url()}/{table}?{match_column}=eq.{match_value}"
        response = httpx.delete(url, headers=get_headers(), timeout=30)
        if response.status_code in [200, 204]:
            return True
        else:
            st.error(f"DB Delete Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Delete Error: {e}")
        return None


# ============================================================
# BARCODE GENERATION (Pure Python SVG - Code128B)
# ============================================================
CODE128B_START = 104
CODE128_STOP = 106

CODE128B_PATTERNS = {
    0: "11011001100", 1: "11001101100", 2: "11001100110", 3: "10010011000",
    4: "10010001100", 5: "10001001100", 6: "10011001000", 7: "10011000100",
    8: "10001100100", 9: "11001001000", 10: "11001000100", 11: "11000100100",
    12: "10110011100", 13: "10011011100", 14: "10011001110", 15: "10111001100",
    16: "10011101100", 17: "10011100110", 18: "11001110010", 19: "11001011100",
    20: "11001001110", 21: "11011100100", 22: "11001110100", 23: "11101101110",
    24: "11101001100", 25: "11100101100", 26: "11100100110", 27: "11101100100",
    28: "11100110100", 29: "11100110010", 30: "11011011000", 31: "11011000110",
    32: "11000110110", 33: "10100011000", 34: "10001011000", 35: "10001000110",
    36: "10110001000", 37: "10001101000", 38: "10001100010", 39: "11010001000",
    40: "11000101000", 41: "11000100010", 42: "10110111000", 43: "10110001110",
    44: "10001101110", 45: "10111011000", 46: "10111000110", 47: "10001110110",
    48: "11101110110", 49: "11010001110", 50: "11000101110", 51: "11011101000",
    52: "11011100010", 53: "11011101110", 54: "11101011000", 55: "11101000110",
    56: "11100010110", 57: "11101101000", 58: "11101100010", 59: "11100011010",
    60: "11101111010", 61: "11001000010", 62: "11110001010", 63: "10100110000",
    64: "10100001100", 65: "10010110000", 66: "10010000110", 67: "10000101100",
    68: "10000100110", 69: "10110010000", 70: "10110000100", 71: "10011010000",
    72: "10011000010", 73: "10000110100", 74: "10000110010", 75: "11000010010",
    76: "11001010000", 77: "11110111010", 78: "11000010100", 79: "10001111010",
    80: "10100111100", 81: "10010111100", 82: "10010011110", 83: "10111100100",
    84: "10011110100", 85: "10011110010", 86: "11110100100", 87: "11110010100",
    88: "11110010010", 89: "11011011110", 90: "11011110110", 91: "11110110110",
    92: "10101111000", 93: "10100011110", 94: "10001011110", 95: "10111101000",
    96: "10111100010", 97: "11110101000", 98: "11110100010", 99: "10111011110",
    100: "10111101110", 101: "11101011110", 102: "11110101110",
    103: "11010000100", 104: "11010010000", 105: "11010011100",
    106: "1100011101011",
}


def encode_code128b(text):
    values = [CODE128B_START]
    for ch in text:
        code = ord(ch) - 32
        if 0 <= code <= 95:
            values.append(code)
        else:
            values.append(0)
    checksum = values[0]
    for i, v in enumerate(values[1:], 1):
        checksum += i * v
    checksum %= 103
    values.append(checksum)
    values.append(CODE128_STOP)
    pattern = ""
    for v in values:
        pattern += CODE128B_PATTERNS.get(v, "")
    return pattern


def generate_barcode_svg(text, width=300, height=80, bar_width=2):
    pattern = encode_code128b(text)
    barcode_width = len(pattern) * bar_width
    svg_width = max(width, barcode_width + 20)
    x_offset = (svg_width - barcode_width) // 2
    bars = []
    for i, bit in enumerate(pattern):
        if bit == '1':
            x = x_offset + i * bar_width
            bars.append(f'<rect x="{x}" y="10" width="{bar_width}" height="{height - 30}" fill="black"/>')
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" height="{height + 10}" viewBox="0 0 {svg_width} {height + 10}">
        <rect width="{svg_width}" height="{height + 10}" fill="white"/>
        {''.join(bars)}
        <text x="{svg_width // 2}" y="{height}" text-anchor="middle" font-family="monospace" font-size="12" fill="black">{text}</text>
    </svg>'''
    return svg


def generate_asset_label_svg(asset_code, asset_name, category, location, temple_name):
    pattern = encode_code128b(asset_code)
    bar_width = 2
    barcode_width = len(pattern) * bar_width
    label_width = max(400, barcode_width + 40)
    label_height = 200
    x_offset = (label_width - barcode_width) // 2
    bars = []
    for i, bit in enumerate(pattern):
        if bit == '1':
            x = x_offset + i * bar_width
            bars.append(f'<rect x="{x}" y="70" width="{bar_width}" height="60" fill="black"/>')
    disp_name = (asset_name[:35] + "...") if len(asset_name) > 35 else asset_name
    disp_temple = (temple_name[:40] + "...") if len(temple_name) > 40 else temple_name
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{label_width}" height="{label_height}" viewBox="0 0 {label_width} {label_height}">
        <rect width="{label_width}" height="{label_height}" fill="white" stroke="black" stroke-width="2" rx="8"/>
        <rect x="0" y="0" width="{label_width}" height="30" fill="#8B0000" rx="8"/>
        <rect x="0" y="15" width="{label_width}" height="15" fill="#8B0000"/>
        <text x="{label_width // 2}" y="20" text-anchor="middle" font-family="Arial,sans-serif" font-size="11" fill="#FFD700" font-weight="bold">{disp_temple}</text>
        <text x="{label_width // 2}" y="48" text-anchor="middle" font-family="Arial,sans-serif" font-size="13" fill="#333" font-weight="bold">{disp_name}</text>
        <text x="{label_width // 2}" y="63" text-anchor="middle" font-family="Arial,sans-serif" font-size="10" fill="#666">{category} | {location}</text>
        {''.join(bars)}
        <text x="{label_width // 2}" y="148" text-anchor="middle" font-family="monospace" font-size="14" fill="black" font-weight="bold">{asset_code}</text>
        <text x="{label_width // 2}" y="168" text-anchor="middle" font-family="Arial,sans-serif" font-size="8" fill="#999">TEMPLE ASSET - DO NOT REMOVE</text>
        <line x1="10" y1="178" x2="{label_width - 10}" y2="178" stroke="#ddd" stroke-width="1" stroke-dasharray="4,2"/>
        <text x="{label_width // 2}" y="192" text-anchor="middle" font-family="Arial,sans-serif" font-size="8" fill="#aaa">Scan barcode for asset details</text>
    </svg>'''
    return svg


def generate_bulk_labels_html(assets, temple_name):
    labels_html = []
    for a in assets:
        svg = generate_asset_label_svg(
            a.get('asset_code', ''), a.get('name', ''),
            a.get('category_name', ''), a.get('location', 'N/A'), temple_name
        )
        svg_b64 = base64.b64encode(svg.encode()).decode()
        labels_html.append(f'''
            <div style="display:inline-block;margin:8px;page-break-inside:avoid;">
                <img src="data:image/svg+xml;base64,{svg_b64}" style="width:400px;height:200px;"/>
            </div>''')
    html = f'''<!DOCTYPE html>
    <html><head><title>Asset Barcode Labels - {temple_name}</title>
    <style>
        @media print {{ body {{ margin: 0; padding: 10mm; }} .no-print {{ display: none !important; }} }}
        body {{ font-family: Arial, sans-serif; text-align: center; }}
        .label-container {{ display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; padding: 20px; }}
    </style></head><body>
        <div class="no-print" style="padding:15px;background:#8B0000;color:#FFD700;margin-bottom:20px;">
            <h2>{temple_name} - Asset Barcode Labels</h2>
            <p>Total Labels: {len(assets)} | <button onclick="window.print()" style="padding:8px 20px;font-size:14px;cursor:pointer;background:#FFD700;border:none;border-radius:5px;font-weight:bold;">Print Labels</button></p>
        </div>
        <div class="label-container">{''.join(labels_html)}</div>
    </body></html>'''
    return html


def generate_asset_code(category_prefix, sequence_num):
    return f"AST-{category_prefix}-{sequence_num:05d}"


def get_category_prefix(category_name):
    words = category_name.upper().replace('&', '').split()
    if len(words) >= 2:
        return (words[0][:2] + words[1][0])[:3]
    return category_name.upper()[:3]


# ============================================================
# CSS
# ============================================================
def load_css():
    st.markdown("""
    <style>
        .main-header {
            background: linear-gradient(135deg, #8B0000, #DC143C);
            color: #FFD700; padding: 15px 25px; border-radius: 12px;
            margin-bottom: 20px; text-align: center;
            box-shadow: 0 4px 15px rgba(139,0,0,0.3);
        }
        .main-header h1 { color: #FFD700; font-size: 1.5em; margin: 0; }
        .main-header h3 { color: rgba(255,215,0,0.8); font-size: 0.9em; margin: 2px 0; }
        .main-header p { color: rgba(255,248,220,0.8); font-size: 0.75em; margin: 0; }
        .stat-card {
            border-radius: 15px; padding: 20px; color: white;
            box-shadow: 0 5px 20px rgba(0,0,0,0.15); margin-bottom: 15px;
        }
        .stat-card.income { background: linear-gradient(135deg, #228B22, #32CD32); }
        .stat-card.expense { background: linear-gradient(135deg, #DC143C, #FF4500); }
        .stat-card.devotees { background: linear-gradient(135deg, #4169E1, #6495ED); }
        .stat-card.bills { background: linear-gradient(135deg, #FF8C00, #FFD700); }
        .stat-card.assets { background: linear-gradient(135deg, #6B3FA0, #9B59B6); }
        .stat-card.asset-value { background: linear-gradient(135deg, #1ABC9C, #16A085); }
        .stat-card h4 { font-size: 0.85em; opacity: 0.9; margin-bottom: 5px; }
        .stat-card h2 { font-size: 1.8em; font-weight: 700; margin: 0; }
        .pooja-card {
            background: linear-gradient(135deg, #FFF8DC, #FFEFD5);
            border: 1px solid #FFD700; border-radius: 10px; padding: 12px;
            margin-bottom: 8px; border-left: 4px solid #8B0000;
        }
        .news-ticker {
            background: linear-gradient(90deg, #8B0000, #DC143C, #8B0000);
            color: #FFD700; padding: 10px 20px; border-radius: 10px;
            margin-bottom: 15px; text-align: center;
        }
        .family-card {
            background: #f8f9fa; border: 1px solid #dee2e6;
            border-radius: 10px; padding: 12px; margin-bottom: 8px;
        }
        .yearly-pooja-card {
            background: #FFF8DC; border: 1px solid #FFD700;
            border-radius: 8px; padding: 8px 12px; margin-bottom: 6px;
        }
        .bill-receipt {
            background: white; padding: 25px; border-radius: 12px;
            box-shadow: 0 2px 15px rgba(0,0,0,0.08); border: 2px solid #FFD700;
        }
        .asset-card {
            background: linear-gradient(135deg, #f8f9fa, #ffffff);
            border: 1px solid #dee2e6; border-radius: 12px;
            padding: 15px; margin-bottom: 10px;
            border-left: 5px solid #6B3FA0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        .asset-badge {
            display: inline-block; padding: 3px 10px; border-radius: 12px;
            font-size: 0.75em; font-weight: 600; margin: 2px;
        }
        .badge-new { background: #d4edda; color: #155724; }
        .badge-good { background: #cce5ff; color: #004085; }
        .badge-fair { background: #fff3cd; color: #856404; }
        .badge-poor { background: #f8d7da; color: #721c24; }
        .badge-damaged { background: #721c24; color: white; }
        .barcode-label {
            background: white; border: 2px dashed #ccc; border-radius: 10px;
            padding: 15px; margin: 8px; text-align: center;
            display: inline-block;
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #8B0000, #B22222, #DC143C);
        }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] { color: #FFF8DC; }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)


# ============================================================
# SESSION STATE
# ============================================================
def init_session():
    defaults = {
        'logged_in': False, 'user_id': None, 'username': None,
        'full_name': None, 'role': None, 'page': 'dashboard',
        'edit_devotee_id': None, 'view_devotee_id': None,
        'view_bill_id': None, 'edit_samaya_id': None,
        'edit_mandapam_id': None, 'edit_asset_id': None,
        'view_asset_id': None, 'print_asset_ids': [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def is_admin():
    return st.session_state.get('role') == 'admin'


def go_to(page, **kwargs):
    st.session_state['page'] = page
    for k, v in kwargs.items():
        st.session_state[k] = v
    st.rerun()


# ============================================================
# LOGIN
# ============================================================
def login_page():
    st.markdown(f"""
    <div style="text-align:center; padding:30px;">
        <div style="font-size:80px;">🕉️</div>
        <h1 style="color:#8B0000;">{TEMPLE_NAME}</h1>
        <h3 style="color:#DC143C;">{TEMPLE_TRUST}</h3>
        <p style="color:#666;">{TEMPLE_ADDRESS_LINE3}</p>
        <hr style="border-color:#FFD700; width:50%; margin:15px auto;">
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        with st.form("login"):
            username = st.text_input("👤 Username")
            password = st.text_input("🔒 Password", type="password")
            btn = st.form_submit_button("🔑 Login", use_container_width=True)
            if btn and username and password:
                users = db_select("users", filters={"username": username, "is_active_user": True})
                if users:
                    user = users[0]
                    if check_password_hash(user['password_hash'], password):
                        st.session_state['logged_in'] = True
                        st.session_state['user_id'] = user['id']
                        st.session_state['username'] = user['username']
                        st.session_state['full_name'] = user.get('full_name') or user['username']
                        st.session_state['role'] = user['role']
                        st.success("Welcome! 🙏")
                        st.rerun()
                    else:
                        st.error("❌ Wrong password!")
                else:
                    st.error("❌ User not found!")
            elif btn:
                st.warning("Enter username and password")


# ============================================================
# SIDEBAR
# ============================================================
def sidebar():
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align:center; padding:10px;">
            <div style="font-size:50px;">🕉️</div>
            <h4 style="color:#FFD700; font-size:0.85em;">{TEMPLE_NAME}</h4>
            <p style="color:rgba(255,215,0,0.7); font-size:0.7em;">{TEMPLE_TRUST}</p>
            <p style="color:#FFD700; font-size:0.75em;">
                👤 {st.session_state['full_name']}
                {"🔴 ADMIN" if is_admin() else ""}
            </p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")

        menu = [
            ("📊 Dashboard", "dashboard"),
            ("👥 Devotees", "devotees"),
            ("🧾 Billing", "billing"),
            ("💸 Expenses", "expenses"),
            ("📈 Reports", "reports"),
            (None, None),
            ("📦 Assets & Barcode", "assets"),
            ("📊 Asset Reports", "asset_reports"),
            (None, None),
            ("🎓 Samaya Vakuppu", "samaya"),
            ("🏛️ Mandapam", "mandapam"),
            ("🙏 Daily Pooja", "daily_pooja"),
            ("⚙️ Settings", "settings"),
        ]
        if is_admin():
            menu += [(None, None), ("👤 Users", "users"), ("🗑️ Deleted Bills", "deleted_bills")]

        for label, page in menu:
            if label is None:
                st.markdown("---")
            else:
                if st.button(label, key=f"m_{page}", use_container_width=True):
                    go_to(page)

        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()


# ============================================================
# DASHBOARD
# ============================================================
def page_dashboard():
    st.markdown(f"""<div class="main-header">
        <h1>🕉️ {TEMPLE_NAME}</h1><h3>{TEMPLE_TRUST}</h3>
        <p>{TEMPLE_ADDRESS_LINE3}</p></div>""", unsafe_allow_html=True)

    period = st.radio("Period:", ['Daily', 'Weekly', 'Monthly', 'Yearly'],
                       horizontal=True, label_visibility="collapsed")

    today_d = date.today()
    if period == 'Daily':
        sd, ed = today_d, today_d
    elif period == 'Weekly':
        sd, ed = today_d - timedelta(days=today_d.weekday()), today_d
    elif period == 'Monthly':
        sd, ed = today_d.replace(day=1), today_d
    else:
        sd, ed = today_d.replace(month=1, day=1), today_d

    bills = db_select("bill", "amount,bill_date", filters={"is_deleted": False})
    pb = [b for b in bills if sd.isoformat() <= str(b.get('bill_date', ''))[:10] <= ed.isoformat()]
    ti = sum(float(b.get('amount', 0) or 0) for b in pb)

    exps = db_select("expense", "amount,expense_date")
    pe = [e for e in exps if sd.isoformat() <= str(e.get('expense_date', ''))[:10] <= ed.isoformat()]
    te = sum(float(e.get('amount', 0) or 0) for e in pe)

    devs = db_select("devotee", "id", filters={"is_family_head": True, "is_active": True})
    td_count = len(devs)

    all_assets = db_select("asset", "id,purchase_value", filters={"is_active": True})
    asset_count = len(all_assets)
    asset_value = sum(float(a.get('purchase_value', 0) or 0) for a in all_assets)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.markdown(f'<div class="stat-card income"><h4>⬆️ Income</h4><h2>₹{ti:,.0f}</h2></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="stat-card expense"><h4>⬇️ Expenses</h4><h2>₹{te:,.0f}</h2></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="stat-card devotees"><h4>👥 Devotees</h4><h2>{td_count}</h2></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="stat-card bills"><h4>🧾 Bills</h4><h2>{len(pb)}</h2></div>', unsafe_allow_html=True)
    with c5:
        st.markdown(f'<div class="stat-card assets"><h4>📦 Assets</h4><h2>{asset_count}</h2></div>', unsafe_allow_html=True)
    with c6:
        st.markdown(f'<div class="stat-card asset-value"><h4>💎 Asset Value</h4><h2>₹{asset_value:,.0f}</h2></div>', unsafe_allow_html=True)

    all_devs = db_select("devotee", "name,mobile_no,dob", filters={"is_active": True})
    bdays = [d for d in all_devs if d.get('dob') and str(d['dob'])[5:10] == today_d.strftime('%m-%d')]
    if bdays:
        txt = " | ".join([f"🎂 Happy Birthday {b['name']}!" for b in bdays])
        st.markdown(f'<div class="news-ticker">{txt}</div>', unsafe_allow_html=True)

    cl, cr = st.columns(2)
    with cl:
        st.markdown("### 🙏 Today's Pooja")
        poojas = db_select("daily_pooja", filters={"is_active": True}, order="pooja_time")
        for p in poojas:
            st.markdown(f"""<div class="pooja-card">
                <strong>{p['pooja_name']}</strong> —
                <span style="color:#8B0000;font-weight:700;">{p.get('pooja_time') or 'TBD'}</span>
                <br><small>{p.get('description') or ''}</small></div>""", unsafe_allow_html=True)
        if not poojas:
            st.info("No pooja scheduled")

    with cr:
        st.markdown("### 🎂 Birthdays")
        if bdays:
            for b in bdays:
                st.write(f"🎂 **{b['name']}** — {b.get('mobile_no') or '-'}")
        else:
            st.info("No birthdays today")

    st.markdown("### 🧾 Recent Bills")
    recent = db_select("bill", filters={"is_deleted": False}, order="-bill_date", limit=10)
    if recent:
        import pandas as pd
        for b in recent:
            if b.get('devotee_id'):
                d = db_select("devotee", "name", filters={"id": b['devotee_id']})
                b['name'] = d[0]['name'] if d else '-'
            else:
                b['name'] = b.get('guest_name') or '-'
            if b.get('pooja_type_id'):
                p = db_select("pooja_type", "name", filters={"id": b['pooja_type_id']})
                b['pooja'] = p[0]['name'] if p else '-'
            else:
                b['pooja'] = '-'
        df = pd.DataFrame(recent)
        df['Date'] = df['bill_date'].apply(lambda x: str(x)[:10])
        df['Amount'] = df['amount'].apply(lambda x: f"₹{float(x or 0):,.2f}")
        st.dataframe(df[['bill_number', 'Date', 'name', 'pooja', 'Amount']].rename(
            columns={'bill_number': 'Bill No', 'name': 'Name', 'pooja': 'Pooja'}),
            use_container_width=True, hide_index=True)


# ============================================================
# DEVOTEES
# ============================================================
def page_devotees():
    st.markdown("## 👥 Enrolled Devotees")
    c1, c2 = st.columns([3, 1])
    with c2:
        if st.button("➕ Add Devotee", use_container_width=True):
            go_to('add_devotee', edit_devotee_id=None)

    search = st.text_input("🔍 Search...", placeholder="Name or mobile")
    devotees = db_select("devotee", filters={"is_family_head": True, "is_active": True}, order="name")

    if search:
        sl = search.lower()
        devotees = [d for d in devotees if sl in (d.get('name') or '').lower() or sl in (d.get('mobile_no') or '')]

    if devotees:
        for d in devotees:
            fam = db_select("devotee", "id", filters={"family_head_id": d['id']})
            c1, c2, c3, c4, c5 = st.columns([0.5, 2.5, 2, 1, 2])
            with c1:
                st.write(f"#{d['id']}")
            with c2:
                st.write(f"**{d['name']}**")
            with c3:
                st.write(f"📱 {d.get('mobile_no') or '-'}")
            with c4:
                st.write(f"👨‍👩‍👧 {len(fam)}")
            with c5:
                b1, b2, b3 = st.columns(3)
                with b1:
                    if st.button("👁", key=f"v{d['id']}"):
                        go_to('view_devotee', view_devotee_id=d['id'])
                with b2:
                    if st.button("✏️", key=f"e{d['id']}"):
                        go_to('add_devotee', edit_devotee_id=d['id'])
                with b3:
                    if st.button("🗑", key=f"d{d['id']}"):
                        db_delete("devotee_yearly_pooja", "devotee_id", d['id'])
                        db_delete("devotee", "family_head_id", d['id'])
                        db_delete("devotee", "id", d['id'])
                        st.rerun()
            st.markdown("---")
    else:
        st.info("No devotees found")


def page_add_devotee():
    eid = st.session_state.get('edit_devotee_id')
    dev = None
    if eid:
        r = db_select("devotee", filters={"id": eid})
        dev = r[0] if r else None

    st.markdown(f"## {'✏️ Edit' if dev else '➕ Add'} Devotee")

    with st.form("dev_form"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Name *", value=dev['name'] if dev else "")
            dob_val = None
            if dev and dev.get('dob'):
                try:
                    dob_val = datetime.strptime(str(dev['dob'])[:10], '%Y-%m-%d').date()
                except Exception:
                    pass
            dob = st.date_input("DOB", value=dob_val, min_value=date(1920, 1, 1),
                                max_value=date.today(), format="DD/MM/YYYY")
            ri = RELATION_TYPES.index(dev['relation_type']) + 1 if dev and dev.get('relation_type') in RELATION_TYPES else 0
            relation = st.selectbox("Relation", [''] + RELATION_TYPES, index=ri)
            mobile = st.text_input("Mobile", value=dev.get('mobile_no') or '' if dev else '')

        with c2:
            whatsapp = st.text_input("WhatsApp", value=dev.get('whatsapp_no') or '' if dev else '')
            wed_val = None
            if dev and dev.get('wedding_day'):
                try:
                    wed_val = datetime.strptime(str(dev['wedding_day'])[:10], '%Y-%m-%d').date()
                except Exception:
                    pass
            wedding = st.date_input("Wedding Day", value=wed_val, min_value=date(1920, 1, 1), format="DD/MM/YYYY")
            ni = NATCHATHIRAM_LIST.index(dev['natchathiram']) + 1 if dev and dev.get('natchathiram') in NATCHATHIRAM_LIST else 0
            natch = st.selectbox("Natchathiram", [''] + NATCHATHIRAM_LIST, index=ni)
            address = st.text_area("Address", value=dev.get('address') or '' if dev else '', height=80)

        if st.form_submit_button("💾 Save", use_container_width=True):
            if not name.strip():
                st.error("Name required!")
            else:
                data = {
                    "name": name.strip(),
                    "dob": dob.isoformat() if dob else None,
                    "relation_type": relation or None,
                    "mobile_no": mobile or None,
                    "whatsapp_no": whatsapp or None,
                    "wedding_day": wedding.isoformat() if wedding else None,
                    "natchathiram": natch or None,
                    "address": address or None,
                    "is_family_head": True,
                    "is_active": True
                }
                if eid and dev:
                    db_update("devotee", data, "id", eid)
                    st.success("Updated! ✅")
                else:
                    result = db_insert("devotee", data)
                    if result:
                        st.session_state['edit_devotee_id'] = result['id']
                        st.success(f"Added! ID: {result['id']} ✅")
                        st.rerun()

    cid = eid or st.session_state.get('edit_devotee_id')
    if cid:
        st.markdown("---")
        st.markdown("### 👨‍👩‍👧‍👦 Family Members")
        family = db_select("devotee", filters={"family_head_id": cid}, order="name")
        for fm in family:
            c1, c2, c3 = st.columns([3, 3, 1])
            with c1:
                st.write(f"**{fm['name']}** ({fm.get('relation_type') or '-'})")
            with c2:
                st.write(f"DOB: {str(fm.get('dob') or '-')[:10]} | 📱 {fm.get('mobile_no') or '-'}")
            with c3:
                if st.button("🗑", key=f"rf{fm['id']}"):
                    db_delete("devotee", "id", fm['id'])
                    st.rerun()

        with st.form("add_fm"):
            fc1, fc2, fc3 = st.columns(3)
            with fc1:
                fn = st.text_input("Name", key="fn")
                fd = st.date_input("DOB", key="fd", value=None, min_value=date(1920, 1, 1), format="DD/MM/YYYY")
            with fc2:
                fr = st.selectbox("Relation", [''] + RELATION_TYPES, key="fr")
                fs = st.selectbox("Star", [''] + NATCHATHIRAM_LIST, key="fs")
            with fc3:
                fmob = st.text_input("Mobile", key="fmo")
            if st.form_submit_button("➕ Add Member"):
                if fn.strip():
                    db_insert("devotee", {
                        "name": fn.strip(),
                        "dob": fd.isoformat() if fd else None,
                        "relation_type": fr or None,
                        "natchathiram": fs or None,
                        "mobile_no": fmob or None,
                        "family_head_id": cid,
                        "is_family_head": False,
                        "is_active": True
                    })
                    st.success("Added!")
                    st.rerun()

        st.markdown("---")
        st.markdown("### 🕉️ Yearly Poojas")
        yearly = db_select("devotee_yearly_pooja", filters={"devotee_id": cid})
        for yp in yearly:
            c1, c2, c3 = st.columns([3, 3, 1])
            with c1:
                st.write(f"**{yp.get('pooja_name') or '-'}**")
            with c2:
                st.write(f"{str(yp.get('pooja_date') or '-')[:10]} | {yp.get('notes') or '-'}")
            with c3:
                if st.button("🗑", key=f"ry{yp['id']}"):
                    db_delete("devotee_yearly_pooja", "id", yp['id'])
                    st.rerun()

        pts = db_select("pooja_type", filters={"is_active": True}, order="name")
        with st.form("add_yp"):
            yc1, yc2, yc3 = st.columns(3)
            with yc1:
                pt_names = [f"{p['name']} (₹{p['amount']})" for p in pts]
                yps = st.selectbox("Pooja", [''] + pt_names, key="yps")
            with yc2:
                ypd = st.date_input("Date", key="ypd", format="DD/MM/YYYY")
            with yc3:
                ypn = st.text_input("Notes", key="ypn")
            if st.form_submit_button("➕ Add Pooja"):
                if yps:
                    idx = pt_names.index(yps)
                    pt = pts[idx]
                    db_insert("devotee_yearly_pooja", {
                        "devotee_id": cid,
                        "pooja_type_id": pt['id'],
                        "pooja_name": pt['name'],
                        "pooja_date": ypd.isoformat(),
                        "notes": ypn or None
                    })
                    st.success("Added!")
                    st.rerun()

    if st.button("⬅️ Back to Devotees"):
        go_to('devotees')


def page_view_devotee():
    did = st.session_state.get('view_devotee_id')
    if not did:
        go_to('devotees')
        return
    r = db_select("devotee", filters={"id": did})
    if not r:
        st.error("Not found!")
        return
    d = r[0]

    st.markdown(f"## 👤 {d['name']}")
    c1, c2 = st.columns([1, 3])
    with c1:
        st.markdown(f"""<div style="width:100px;height:100px;background:#8B0000;color:#FFD700;
            border-radius:50%;display:flex;align-items:center;justify-content:center;
            font-size:2.5em;margin:auto;">{d['name'][0]}</div>""", unsafe_allow_html=True)
    with c2:
        cc1, cc2, cc3 = st.columns(3)
        with cc1:
            st.write(f"**DOB:** {str(d.get('dob') or '-')[:10]}")
            st.write(f"**Relation:** {d.get('relation_type') or '-'}")
        with cc2:
            st.write(f"**Mobile:** {d.get('mobile_no') or '-'}")
            st.write(f"**WhatsApp:** {d.get('whatsapp_no') or '-'}")
        with cc3:
            st.write(f"**Wedding:** {str(d.get('wedding_day') or '-')[:10]}")
            st.write(f"**Star:** {d.get('natchathiram') or '-'}")
        st.write(f"**Address:** {d.get('address') or '-'}")

    st.markdown("### 👨‍👩‍👧‍👦 Family")
    for fm in db_select("devotee", filters={"family_head_id": did}):
        st.markdown(f"""<div class="family-card"><strong>{fm['name']}</strong> |
            {fm.get('relation_type') or '-'} | DOB: {str(fm.get('dob') or '-')[:10]} |
            📱 {fm.get('mobile_no') or '-'}</div>""", unsafe_allow_html=True)

    st.markdown("### 🕉️ Yearly Poojas")
    for yp in db_select("devotee_yearly_pooja", filters={"devotee_id": did}):
        st.markdown(f"""<div class="yearly-pooja-card"><strong>{yp.get('pooja_name') or '-'}</strong> |
            {str(yp.get('pooja_date') or '-')[:10]} | {yp.get('notes') or '-'}</div>""", unsafe_allow_html=True)

    st.markdown("### 🧾 Bills")
    dbills = db_select("bill", filters={"devotee_id": did, "is_deleted": False}, order="-bill_date")
    if dbills:
        import pandas as pd
        for b in dbills:
            if b.get('pooja_type_id'):
                p = db_select("pooja_type", "name", filters={"id": b['pooja_type_id']})
                b['pooja'] = p[0]['name'] if p else '-'
            else:
                b['pooja'] = '-'
        df = pd.DataFrame(dbills)
        df['Date'] = df['bill_date'].apply(lambda x: str(x)[:10])
        df['Amount'] = df['amount'].apply(lambda x: f"₹{float(x or 0):,.2f}")
        st.dataframe(df[['bill_number', 'Date', 'pooja', 'Amount']].rename(
            columns={'bill_number': 'Bill', 'pooja': 'Pooja'}),
            use_container_width=True, hide_index=True)

    bc1, bc2 = st.columns(2)
    with bc1:
        if st.button("✏️ Edit"):
            go_to('add_devotee', edit_devotee_id=did)
    with bc2:
        if st.button("⬅️ Back"):
            go_to('devotees')


# ============================================================
# BILLING
# ============================================================
def page_billing():
    st.markdown("## 🧾 Bills")
    c1, c2 = st.columns([3, 1])
    with c2:
        if st.button("➕ New Bill", use_container_width=True):
            go_to('new_bill')

    fc1, fc2 = st.columns(2)
    with fc1:
        fd = st.date_input("From", value=date.today(), format="DD/MM/YYYY", key="bf")
    with fc2:
        td = st.date_input("To", value=date.today(), format="DD/MM/YYYY", key="bt")

    all_bills = db_select("bill", order="-bill_date")
    fbills = [b for b in all_bills if fd.isoformat() <= str(b.get('bill_date', ''))[:10] <= td.isoformat()]

    if fbills:
        for b in fbills:
            if b.get('is_deleted'):
                st.markdown(f"~~{b['bill_number']} | DELETED~~")
                continue
            if b.get('devotee_id'):
                dd = db_select("devotee", "name", filters={"id": b['devotee_id']})
                bname = dd[0]['name'] if dd else '-'
            else:
                bname = b.get('guest_name') or '-'
            c1, c2, c3, c4, c5 = st.columns([1.5, 1.5, 2, 1.5, 1.5])
            with c1:
                st.write(f"**{b['bill_number']}**")
            with c2:
                st.write(str(b.get('bill_date', ''))[:10])
            with c3:
                st.write(bname)
            with c4:
                st.write(f"**₹{float(b.get('amount', 0)):,.2f}**")
            with c5:
                if st.button("👁", key=f"vb{b['id']}"):
                    go_to('view_bill', view_bill_id=b['id'])
                if is_admin() and st.button("🗑", key=f"db{b['id']}"):
                    db_update("bill", {
                        "is_deleted": True,
                        "deleted_by": st.session_state['user_id'],
                        "deleted_at": datetime.now().isoformat(),
                        "delete_reason": "Admin deleted"
                    }, "id", b['id'])
                    st.rerun()
            st.markdown("---")
    else:
        st.info("No bills found")


def page_new_bill():
    st.markdown("## 🧾 New Bill")
    pts = db_select("pooja_type", filters={"is_active": True}, order="name")
    devs = db_select("devotee", "id,name,mobile_no,address",
                     filters={"is_family_head": True, "is_active": True}, order="name")

    last = db_select("bill", "id", order="-id", limit=1)
    lid = last[0]['id'] if last else 0
    nbn = f"BILL-{lid + 1:06d}"

    with st.form("bill_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.text_input("Bill No", value=nbn, disabled=True)
        with c2:
            manual = st.text_input("Manual Bill No")
        with c3:
            bdate = st.date_input("Date", value=date.today(), format="DD/MM/YYYY")

        dtype = st.radio("Type:", ["Enrolled", "Guest"], horizontal=True)

        dev_id = guest_name = guest_mobile = guest_address = guest_whatsapp = None
        if dtype == "Enrolled":
            dopts = {f"{d['name']} (ID:{d['id']})": d['id'] for d in devs}
            sd = st.selectbox("Devotee *", [''] + list(dopts.keys()))
            dev_id = dopts.get(sd)
        else:
            gc1, gc2 = st.columns(2)
            with gc1:
                guest_name = st.text_input("Guest Name *")
                guest_mobile = st.text_input("Guest Mobile")
            with gc2:
                guest_address = st.text_area("Address", height=68)
                guest_whatsapp = st.text_input("WhatsApp")

        pc1, pc2, pc3 = st.columns(3)
        with pc1:
            ptopts = {f"{p['name']} (₹{p['amount']})": p for p in pts}
            spt = st.selectbox("Pooja *", [''] + list(ptopts.keys()))
        with pc2:
            damt = float(ptopts[spt]['amount']) if spt else 0.0
            amount = st.number_input("Amount *", value=damt, step=10.0)
        with pc3:
            notes = st.text_input("Notes")

        if st.form_submit_button("💾 Create Bill", use_container_width=True):
            if not spt:
                st.error("Select pooja!")
            elif dtype == "Enrolled" and not dev_id:
                st.error("Select devotee!")
            elif dtype == "Guest" and not guest_name:
                st.error("Enter guest name!")
            else:
                pt = ptopts[spt]
                result = db_insert("bill", {
                    "bill_number": nbn,
                    "manual_bill_no": manual or None,
                    "bill_book_no": None,
                    "bill_date": datetime.combine(bdate, datetime.now().time()).isoformat(),
                    "devotee_type": dtype.lower(),
                    "devotee_id": dev_id,
                    "guest_name": guest_name,
                    "guest_address": guest_address,
                    "guest_mobile": guest_mobile,
                    "guest_whatsapp": guest_whatsapp,
                    "pooja_type_id": pt['id'],
                    "amount": amount,
                    "notes": notes or None,
                    "created_by": st.session_state['user_id'],
                    "is_deleted": False
                })
                if result:
                    st.success(f"Bill {nbn} created! ✅")
                    go_to('view_bill', view_bill_id=result['id'])

    if st.button("⬅️ Back"):
        go_to('billing')


def page_view_bill():
    bid = st.session_state.get('view_bill_id')
    if not bid:
        go_to('billing')
        return
    r = db_select("bill", filters={"id": bid})
    if not r:
        st.error("Not found!")
        return
    b = r[0]

    if b.get('devotee_id'):
        dd = db_select("devotee", filters={"id": b['devotee_id']})
        bname = dd[0]['name'] if dd else '-'
        bmob = dd[0].get('mobile_no', '-') if dd else '-'
        baddr = dd[0].get('address', '-') if dd else '-'
    else:
        bname = b.get('guest_name') or '-'
        bmob = b.get('guest_mobile') or '-'
        baddr = b.get('guest_address') or '-'

    pname = '-'
    if b.get('pooja_type_id'):
        pp = db_select("pooja_type", "name", filters={"id": b['pooja_type_id']})
        if pp:
            pname = pp[0]['name']

    amt = float(b.get('amount', 0) or 0)
    bdt = str(b.get('bill_date', ''))[:16].replace('T', ' ')

    st.markdown(f"""<div class="bill-receipt">
        <div style="text-align:center;border-bottom:3px double #8B0000;padding-bottom:12px;margin-bottom:15px;">
            <h2 style="color:#8B0000;">🕉️ {TEMPLE_NAME}</h2>
            <h4 style="color:#DC143C;">{TEMPLE_TRUST}</h4>
            <p style="color:#555;">{TEMPLE_ADDRESS_LINE3}</p>
            <p>📜 BILL RECEIPT</p></div>
        <table style="width:100%;margin-bottom:15px;">
            <tr><td><b>Bill:</b> {b['bill_number']}</td>
                <td><b>Manual:</b> {b.get('manual_bill_no') or '-'}</td>
                <td style="text-align:right;"><b>Date:</b> {bdt}</td></tr>
            <tr><td><b>Name:</b> {bname}</td><td><b>Mobile:</b> {bmob}</td>
                <td style="text-align:right;"><b>Address:</b> {baddr}</td></tr></table>
        <table style="width:100%;border-collapse:collapse;">
            <thead><tr style="background:#8B0000;color:white;">
                <th style="padding:8px;">Pooja</th><th style="padding:8px;">Notes</th>
                <th style="padding:8px;text-align:right;">Amount</th></tr></thead>
            <tbody><tr style="border-bottom:1px solid #ddd;">
                <td style="padding:8px;">{pname}</td><td style="padding:8px;">{b.get('notes') or '-'}</td>
                <td style="padding:8px;text-align:right;"><b>₹{amt:,.2f}</b></td></tr></tbody>
            <tfoot><tr style="border-top:2px solid #8B0000;">
                <td colspan="2" style="padding:8px;text-align:right;"><b>Total:</b></td>
                <td style="padding:8px;text-align:right;color:#8B0000;font-size:1.3em;">
                    <b>₹{amt:,.2f}</b></td></tr></tfoot></table>
        <div style="text-align:center;margin-top:15px;border-top:1px dashed #ccc;padding-top:10px;">
            <small style="color:#888;">{TEMPLE_FULL_ADDRESS}</small></div></div>""", unsafe_allow_html=True)

    if st.button("⬅️ Back"):
        go_to('billing')


# ============================================================
# EXPENSES
# ============================================================
def page_expenses():
    st.markdown("## 💸 Expenses")
    fc1, fc2 = st.columns(2)
    with fc1:
        fd = st.date_input("From", value=date.today().replace(day=1), format="DD/MM/YYYY", key="ef")
    with fc2:
        td = st.date_input("To", value=date.today(), format="DD/MM/YYYY", key="et")

    ets = db_select("expense_type", filters={"is_active": True}, order="name")
    et_map = {e['id']: e['name'] for e in ets}

    all_exp = db_select("expense", order="-expense_date")
    fexps = [e for e in all_exp if fd.isoformat() <= str(e.get('expense_date', ''))[:10] <= td.isoformat()]

    total = sum(float(e.get('amount', 0) or 0) for e in fexps)
    st.markdown(f"**Total: ₹{total:,.2f}**")

    if fexps:
        import pandas as pd
        for e in fexps:
            e['type'] = et_map.get(e.get('expense_type_id'), '-')
        df = pd.DataFrame(fexps)
        df['Date'] = df['expense_date'].apply(lambda x: str(x)[:10])
        df['Amount'] = df['amount'].apply(lambda x: f"₹{float(x or 0):,.2f}")
        st.dataframe(df[['id', 'Date', 'type', 'description', 'Amount']].rename(
            columns={'id': 'ID', 'type': 'Type', 'description': 'Description'}),
            use_container_width=True, hide_index=True)

        del_id = st.number_input("Delete ID:", min_value=0, step=1, value=0)
        if del_id > 0 and st.button("🗑 Delete"):
            db_delete("expense", "id", del_id)
            st.rerun()

    st.markdown("### ➕ Add Expense")
    with st.form("add_exp"):
        ec1, ec2, ec3 = st.columns(3)
        with ec1:
            en = [e['name'] for e in ets]
            se = st.selectbox("Type *", en if en else ['None'])
        with ec2:
            ea = st.number_input("Amount *", min_value=0.0, step=10.0)
        with ec3:
            ed = st.date_input("Date", value=date.today(), format="DD/MM/YYYY")
        edesc = st.text_input("Description")
        if st.form_submit_button("💾 Save"):
            if ea > 0 and ets:
                exp_type_id = next(e['id'] for e in ets if e['name'] == se)
                db_insert("expense", {
                    "expense_type_id": exp_type_id,
                    "amount": ea,
                    "description": edesc or None,
                    "expense_date": ed.isoformat(),
                    "created_by": st.session_state['user_id']
                })
                st.success("Added! ✅")
                st.rerun()


# ============================================================
# REPORTS
# ============================================================
def page_reports():
    st.markdown("## 📈 Reports")
    fc1, fc2 = st.columns(2)
    with fc1:
        fd = st.date_input("From", value=date.today().replace(day=1), format="DD/MM/YYYY", key="rf")
    with fc2:
        td = st.date_input("To", value=date.today(), format="DD/MM/YYYY", key="rt")

    bills = db_select("bill", "amount,pooja_type_id,bill_date", filters={"is_deleted": False})
    pb = [b for b in bills if fd.isoformat() <= str(b.get('bill_date', ''))[:10] <= td.isoformat()]
    ti = sum(float(b.get('amount', 0) or 0) for b in pb)

    exps = db_select("expense", "amount,expense_type_id,expense_date")
    pe = [e for e in exps if fd.isoformat() <= str(e.get('expense_date', ''))[:10] <= td.isoformat()]
    te = sum(float(e.get('amount', 0) or 0) for e in pe)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div class="stat-card income"><h4>Income</h4><h2>₹{ti:,.2f}</h2></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="stat-card expense"><h4>Expenses</h4><h2>₹{te:,.2f}</h2></div>', unsafe_allow_html=True)
    with c3:
        color = "income" if ti - te >= 0 else "expense"
        st.markdown(f'<div class="stat-card {color}"><h4>Net</h4><h2>₹{ti - te:,.2f}</h2></div>', unsafe_allow_html=True)

    cl, cr = st.columns(2)
    with cl:
        st.markdown("### Income by Pooja")
        all_pts = db_select("pooja_type", order="name")
        pt_map = {p['id']: p['name'] for p in all_pts}
        ibp = {}
        for b in pb:
            pn = pt_map.get(b.get('pooja_type_id'), 'Other')
            if pn not in ibp:
                ibp[pn] = {'count': 0, 'total': 0}
            ibp[pn]['count'] += 1
            ibp[pn]['total'] += float(b.get('amount', 0) or 0)
        if ibp:
            import pandas as pd
            st.dataframe(pd.DataFrame([{'Pooja': k, 'Count': v['count'], 'Amount': f"₹{v['total']:,.2f}"}
                                        for k, v in ibp.items()]), use_container_width=True, hide_index=True)

    with cr:
        st.markdown("### Expenses by Type")
        all_ets = db_select("expense_type", order="name")
        et_map = {e['id']: e['name'] for e in all_ets}
        ebt = {}
        for e in pe:
            en = et_map.get(e.get('expense_type_id'), 'Other')
            if en not in ebt:
                ebt[en] = {'count': 0, 'total': 0}
            ebt[en]['count'] += 1
            ebt[en]['total'] += float(e.get('amount', 0) or 0)
        if ebt:
            import pandas as pd
            st.dataframe(pd.DataFrame([{'Type': k, 'Count': v['count'], 'Amount': f"₹{v['total']:,.2f}"}
                                        for k, v in ebt.items()]), use_container_width=True, hide_index=True)


# ============================================================
# ASSETS & BARCODE - MAIN PAGE
# ============================================================
def page_assets():
    st.markdown("## 📦 Temple Assets & Barcode Management")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Asset Inventory", "➕ Add Asset", "🏷️ Categories", "🖨️ Print Barcodes"
    ])

    with tab1:
        _asset_inventory_tab()
    with tab2:
        _asset_add_edit_tab()
    with tab3:
        _asset_categories_tab()
    with tab4:
        _asset_print_barcodes_tab()


def _asset_inventory_tab():
    st.markdown("### 📋 Asset Inventory")

    fc1, fc2, fc3, fc4 = st.columns(4)
    cats = db_select("asset_category", filters={"is_active": True}, order="name")
    cat_names = ['All Categories'] + [c['name'] for c in cats]
    cat_map = {c['name']: c['id'] for c in cats}

    with fc1:
        search = st.text_input("🔍 Search asset...", placeholder="Name, code, or location", key="ast_search")
    with fc2:
        sel_cat = st.selectbox("Category", cat_names, key="ast_cat_filter")
    with fc3:
        sel_cond = st.selectbox("Condition", ['All'] + ASSET_CONDITIONS, key="ast_cond_filter")
    with fc4:
        sel_loc = st.text_input("📍 Location filter", key="ast_loc_filter")

    assets = db_select("asset", filters={"is_active": True}, order="asset_code")
    cat_id_map = {c['id']: c['name'] for c in cats}

    if sel_cat != 'All Categories' and sel_cat in cat_map:
        cid = cat_map[sel_cat]
        assets = [a for a in assets if a.get('category_id') == cid]
    if sel_cond != 'All':
        assets = [a for a in assets if a.get('condition') == sel_cond]
    if sel_loc:
        loc_l = sel_loc.lower()
        assets = [a for a in assets if loc_l in (a.get('location') or '').lower()]
    if search:
        sl = search.lower()
        assets = [a for a in assets if
                  sl in (a.get('name') or '').lower() or
                  sl in (a.get('asset_code') or '').lower() or
                  sl in (a.get('location') or '').lower() or
                  sl in (a.get('description') or '').lower()]

    total_val = sum(float(a.get('purchase_value', 0) or 0) for a in assets)
    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        st.markdown(f'<div class="stat-card assets"><h4>📦 Total Assets</h4><h2>{len(assets)}</h2></div>', unsafe_allow_html=True)
    with sc2:
        st.markdown(f'<div class="stat-card asset-value"><h4>💎 Total Value</h4><h2>₹{total_val:,.2f}</h2></div>', unsafe_allow_html=True)
    with sc3:
        cats_count = len(set(a.get('category_id') for a in assets if a.get('category_id')))
        st.markdown(f'<div class="stat-card bills"><h4>🏷️ Categories</h4><h2>{cats_count}</h2></div>', unsafe_allow_html=True)

    if assets:
        for a in assets:
            cat_name = cat_id_map.get(a.get('category_id'), 'Uncategorized')
            cond = a.get('condition', 'N/A')
            cond_class = cond.lower().replace(' ', '-') if cond else 'good'
            badge_class = f"badge-{cond_class}" if cond_class in ['new', 'good', 'fair', 'poor', 'damaged'] else 'badge-good'

            ac1, ac2, ac3, ac4, ac5 = st.columns([2.5, 1.5, 1.5, 1.5, 1.5])
            with ac1:
                st.markdown(f"**{a.get('asset_code', '-')}** — {a['name']}")
                st.caption(f"📍 {a.get('location') or '-'}")
            with ac2:
                st.markdown(f"🏷️ {cat_name}")
            with ac3:
                st.markdown(f'<span class="asset-badge {badge_class}">{cond}</span>', unsafe_allow_html=True)
            with ac4:
                st.write(f"**₹{float(a.get('purchase_value', 0) or 0):,.2f}**")
            with ac5:
                bc1, bc2, bc3 = st.columns(3)
                with bc1:
                    if st.button("👁", key=f"va_{a['id']}"):
                        go_to('view_asset', view_asset_id=a['id'])
                with bc2:
                    if st.button("✏️", key=f"ea_{a['id']}"):
                        go_to('edit_asset', edit_asset_id=a['id'])
                with bc3:
                    if st.button("🗑", key=f"da_{a['id']}"):
                        db_update("asset", {"is_active": False}, "id", a['id'])
                        st.rerun()
            st.markdown("---")
    else:
        st.info("No assets found. Add your first asset in the 'Add Asset' tab!")


def _asset_add_edit_tab():
    st.markdown("### ➕ Register New Asset")

    cats = db_select("asset_category", filters={"is_active": True}, order="name")
    if not cats:
        st.warning("⚠️ Please add asset categories first in the 'Categories' tab!")
        return

    cat_opts = {c['name']: c for c in cats}

    with st.form("add_asset_form"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Asset Name *", placeholder="e.g., Brass Pooja Bell")
            sel_cat_name = st.selectbox("Category *", list(cat_opts.keys()))
            quantity = st.number_input("Quantity", value=1, min_value=1, step=1)
            purchase_val = st.number_input("Purchase Value (₹)", value=0.0, step=100.0)
            purchase_date = st.date_input("Purchase/Acquisition Date", value=date.today(), format="DD/MM/YYYY")
        with c2:
            location = st.text_input("Location *", placeholder="e.g., Main Sanctum, Kitchen, Office")
            condition = st.selectbox("Condition", ASSET_CONDITIONS)
            supplier = st.text_input("Supplier / Donor", placeholder="Name of supplier or donor")
            warranty_date = st.date_input("Warranty Expiry", value=None, format="DD/MM/YYYY")
            serial_no = st.text_input("Serial / Model No", placeholder="Manufacturer serial number")

        description = st.text_area("Description / Notes", height=80,
                                   placeholder="Detailed description, dimensions, material, etc.")

        if st.form_submit_button("💾 Register Asset & Generate Barcode", use_container_width=True):
            if not name.strip():
                st.error("Asset name is required!")
            elif not sel_cat_name:
                st.error("Select a category!")
            else:
                cat = cat_opts[sel_cat_name]
                prefix = cat.get('code_prefix') or get_category_prefix(sel_cat_name)

                existing = db_select("asset", "id", filters={"category_id": cat['id']})
                seq = len(existing) + 1
                asset_code = generate_asset_code(prefix, seq)

                check = db_select("asset", "id", filters={"asset_code": asset_code})
                while check:
                    seq += 1
                    asset_code = generate_asset_code(prefix, seq)
                    check = db_select("asset", "id", filters={"asset_code": asset_code})

                result = db_insert("asset", {
                    "asset_code": asset_code,
                    "name": name.strip(),
                    "description": description or None,
                    "category_id": cat['id'],
                    "location": location or None,
                    "condition": condition,
                    "quantity": quantity,
                    "purchase_value": purchase_val,
                    "purchase_date": purchase_date.isoformat() if purchase_date else None,
                    "supplier_donor": supplier or None,
                    "warranty_expiry": warranty_date.isoformat() if warranty_date else None,
                    "serial_number": serial_no or None,
                    "is_active": True,
                    "created_by": st.session_state['user_id'],
                    "created_at": datetime.now().isoformat()
                })

                if result:
                    db_insert("asset_audit_log", {
                        "asset_id": result['id'],
                        "action": "CREATED",
                        "details": f"Asset registered: {name} ({asset_code})",
                        "performed_by": st.session_state['user_id'],
                        "performed_at": datetime.now().isoformat()
                    })
                    st.success(f"✅ Asset registered! Code: **{asset_code}**")
                    st.markdown("---")
                    st.markdown("### 🏷️ Generated Barcode Label")
                    svg = generate_asset_label_svg(
                        asset_code, name.strip(), sel_cat_name,
                        location or 'N/A', TEMPLE_NAME
                    )
                    svg_b64 = base64.b64encode(svg.encode()).decode()
                    st.markdown(f'<div class="barcode-label"><img src="data:image/svg+xml;base64,{svg_b64}"/></div>',
                                unsafe_allow_html=True)
                    st.download_button(
                        "📥 Download Barcode Label (SVG)",
                        data=svg,
                        file_name=f"barcode_{asset_code}.svg",
                        mime="image/svg+xml"
                    )


def _asset_categories_tab():
    st.markdown("### 🏷️ Asset Categories")

    cats = db_select("asset_category", filters={"is_active": True}, order="name")

    if cats:
        for c in cats:
            asset_count = len(db_select("asset", "id", filters={"category_id": c['id'], "is_active": True}))
            cc1, cc2, cc3, cc4 = st.columns([2.5, 1.5, 1.5, 1])
            with cc1:
                st.write(f"**{c['name']}**")
            with cc2:
                st.write(f"Prefix: `{c.get('code_prefix', '-')}`")
            with cc3:
                st.write(f"📦 {asset_count} assets")
            with cc4:
                if asset_count == 0:
                    if st.button("🗑", key=f"dc_{c['id']}"):
                        db_update("asset_category", {"is_active": False}, "id", c['id'])
                        st.rerun()
                else:
                    st.write("🔒")
            st.markdown("---")
    else:
        st.info("No categories yet. Add default categories below!")

    if st.button("🔄 Load Default Categories", use_container_width=True):
        for cat_name in ASSET_DEFAULT_CATEGORIES:
            existing = db_select("asset_category", "id", filters={"name": cat_name})
            if not existing:
                prefix = get_category_prefix(cat_name)
                db_insert("asset_category", {
                    "name": cat_name,
                    "code_prefix": prefix,
                    "is_active": True
                })
        st.success("Default categories loaded! ✅")
        st.rerun()

    st.markdown("### ➕ Add Custom Category")
    with st.form("add_cat"):
        cc1, cc2 = st.columns(2)
        with cc1:
            cn = st.text_input("Category Name *", key="cat_name")
        with cc2:
            cp = st.text_input("Code Prefix (3 chars)", key="cat_prefix", max_chars=3,
                               placeholder="e.g. FUR, VES, ELE")
        if st.form_submit_button("➕ Add Category"):
            if cn.strip():
                prefix = cp.upper().strip() if cp.strip() else get_category_prefix(cn)
                existing = db_select("asset_category", "id", filters={"name": cn.strip()})
                if existing:
                    st.error("Category already exists!")
                else:
                    db_insert("asset_category", {
                        "name": cn.strip(),
                        "code_prefix": prefix[:3],
                        "is_active": True
                    })
                    st.success(f"Added! Prefix: {prefix[:3]} ✅")
                    st.rerun()


def _asset_print_barcodes_tab():
    st.markdown("### 🖨️ Print Barcode Labels")
    st.info("Select assets to generate printable barcode sticker sheets. Use your browser's Print function (Ctrl+P) to print on label paper.")

    cats = db_select("asset_category", filters={"is_active": True}, order="name")
    cat_id_map = {c['id']: c['name'] for c in cats}

    pc1, pc2 = st.columns(2)
    with pc1:
        cat_names_p = ['All'] + [c['name'] for c in cats]
        p_cat = st.selectbox("Filter by Category", cat_names_p, key="print_cat")
    with pc2:
        p_loc = st.text_input("Filter by Location", key="print_loc")

    assets = db_select("asset", filters={"is_active": True}, order="asset_code")

    if p_cat != 'All':
        cid = next((c['id'] for c in cats if c['name'] == p_cat), None)
        if cid:
            assets = [a for a in assets if a.get('category_id') == cid]
    if p_loc:
        pl = p_loc.lower()
        assets = [a for a in assets if pl in (a.get('location') or '').lower()]

    if not assets:
        st.warning("No assets found for the selected filters.")
        return

    st.write(f"**{len(assets)} assets found**")

    sel_ids = st.multiselect(
        "Select assets to print",
        options=[a['id'] for a in assets],
        format_func=lambda x: next(
            (f"{a['asset_code']} - {a['name']}" for a in assets if a['id'] == x), str(x)
        ),
        default=[a['id'] for a in assets],
        key="print_sel"
    )

    lc1, lc2 = st.columns(2)
    with lc1:
        copies = st.number_input("Copies per asset", value=1, min_value=1, max_value=10, step=1)
    with lc2:
        st.write(f"**Total labels: {len(sel_ids) * copies}**")

    if sel_ids and st.button("🖨️ Generate Printable Labels", use_container_width=True, type="primary"):
        selected_assets = [a for a in assets if a['id'] in sel_ids]
        for a in selected_assets:
            a['category_name'] = cat_id_map.get(a.get('category_id'), 'N/A')

        print_list = selected_assets * copies

        st.markdown("### 👁️ Label Preview")
        preview_cols = st.columns(min(3, len(print_list)))
        for i, a in enumerate(print_list[:6]):
            with preview_cols[i % 3]:
                svg = generate_asset_label_svg(
                    a.get('asset_code', ''), a.get('name', ''),
                    a.get('category_name', ''), a.get('location', 'N/A'), TEMPLE_NAME
                )
                svg_b64 = base64.b64encode(svg.encode()).decode()
                st.markdown(f'<div class="barcode-label"><img src="data:image/svg+xml;base64,{svg_b64}" style="width:100%;"/></div>',
                            unsafe_allow_html=True)

        if len(print_list) > 6:
            st.info(f"... and {len(print_list) - 6} more labels")

        html = generate_bulk_labels_html(print_list, TEMPLE_NAME)
        st.download_button(
            "📥 Download Printable HTML (Open in browser & Print)",
            data=html,
            file_name=f"barcode_labels_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
            mime="text/html"
        )

        with st.expander("📥 Download Individual SVGs"):
            for a in selected_assets:
                svg = generate_asset_label_svg(
                    a.get('asset_code', ''), a.get('name', ''),
                    a.get('category_name', ''), a.get('location', 'N/A'), TEMPLE_NAME
                )
                st.download_button(
                    f"📥 {a['asset_code']}",
                    data=svg,
                    file_name=f"barcode_{a['asset_code']}.svg",
                    mime="image/svg+xml",
                    key=f"dl_{a['id']}"
                )


# ============================================================
# VIEW ASSET
# ============================================================
def page_view_asset():
    aid = st.session_state.get('view_asset_id')
    if not aid:
        go_to('assets')
        return
    r = db_select("asset", filters={"id": aid})
    if not r:
        st.error("Asset not found!")
        return
    a = r[0]

    cats = db_select("asset_category", filters={"is_active": True})
    cat_map = {c['id']: c['name'] for c in cats}
    cat_name = cat_map.get(a.get('category_id'), 'Uncategorized')

    cond = a.get('condition', 'N/A')
    cond_class = cond.lower().replace(' ', '-') if cond else 'good'
    badge_class = f"badge-{cond_class}" if cond_class in ['new', 'good', 'fair', 'poor', 'damaged'] else 'badge-good'

    st.markdown(f"## 📦 Asset: {a['name']}")

    bc1, bc2 = st.columns([1, 2])
    with bc1:
        svg = generate_asset_label_svg(
            a.get('asset_code', ''), a.get('name', ''),
            cat_name, a.get('location', 'N/A'), TEMPLE_NAME
        )
        svg_b64 = base64.b64encode(svg.encode()).decode()
        st.markdown(f'<div class="barcode-label"><img src="data:image/svg+xml;base64,{svg_b64}"/></div>',
                    unsafe_allow_html=True)
        st.download_button(
            "📥 Download Label",
            data=svg,
            file_name=f"barcode_{a['asset_code']}.svg",
            mime="image/svg+xml"
        )

    with bc2:
        st.markdown(f"""
        <div class="asset-card" style="border-left-color:#8B0000;">
            <table style="width:100%;">
                <tr><td><b>Asset Code:</b></td><td><code style="font-size:1.2em;background:#FFF8DC;padding:3px 8px;border-radius:4px;">{a.get('asset_code', '-')}</code></td></tr>
                <tr><td><b>Name:</b></td><td>{a['name']}</td></tr>
                <tr><td><b>Category:</b></td><td>🏷️ {cat_name}</td></tr>
                <tr><td><b>Location:</b></td><td>📍 {a.get('location') or '-'}</td></tr>
                <tr><td><b>Condition:</b></td><td><span class="asset-badge {badge_class}">{cond}</span></td></tr>
                <tr><td><b>Quantity:</b></td><td>{a.get('quantity', 1)}</td></tr>
                <tr><td><b>Purchase Value:</b></td><td><b>₹{float(a.get('purchase_value', 0) or 0):,.2f}</b></td></tr>
                <tr><td><b>Purchase Date:</b></td><td>{str(a.get('purchase_date') or '-')[:10]}</td></tr>
                <tr><td><b>Supplier/Donor:</b></td><td>{a.get('supplier_donor') or '-'}</td></tr>
                <tr><td><b>Serial No:</b></td><td>{a.get('serial_number') or '-'}</td></tr>
                <tr><td><b>Warranty Expiry:</b></td><td>{str(a.get('warranty_expiry') or '-')[:10]}</td></tr>
                <tr><td><b>Description:</b></td><td>{a.get('description') or '-'}</td></tr>
            </table>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("### 📜 Audit Trail")
    logs = db_select("asset_audit_log", filters={"asset_id": aid}, order="-performed_at")
    if logs:
        for log in logs:
            usr = '-'
            if log.get('performed_by'):
                u = db_select("users", "full_name", filters={"id": log['performed_by']})
                usr = u[0]['full_name'] if u else '-'
            st.markdown(f"""<div style="padding:6px 12px;background:#f8f9fa;border-radius:6px;margin-bottom:4px;border-left:3px solid #6B3FA0;">
                <small><b>{log.get('action', '-')}</b> — {log.get('details', '-')} | 👤 {usr} | 🕐 {str(log.get('performed_at', ''))[:19]}</small></div>""",
                unsafe_allow_html=True)
    else:
        st.info("No audit logs yet")

    st.markdown("### ➕ Add Audit Entry")
    with st.form("add_audit"):
        auc1, auc2 = st.columns(2)
        with auc1:
            action = st.selectbox("Action", [
                'INSPECTION', 'MAINTENANCE', 'REPAIR', 'MOVED',
                'CONDITION_UPDATE', 'COUNTED', 'NOTE'
            ])
        with auc2:
            new_cond = st.selectbox("Update Condition", ['No Change'] + ASSET_CONDITIONS)
        details = st.text_input("Details / Notes")
        if st.form_submit_button("💾 Add Entry"):
            db_insert("asset_audit_log", {
                "asset_id": aid,
                "action": action,
                "details": details or f"{action} performed",
                "performed_by": st.session_state['user_id'],
                "performed_at": datetime.now().isoformat()
            })
            if new_cond != 'No Change':
                db_update("asset", {"condition": new_cond}, "id", aid)
            st.success("Audit entry added! ✅")
            st.rerun()

    nav1, nav2 = st.columns(2)
    with nav1:
        if st.button("✏️ Edit Asset"):
            go_to('edit_asset', edit_asset_id=aid)
    with nav2:
        if st.button("⬅️ Back to Assets"):
            go_to('assets')


# ============================================================
# EDIT ASSET
# ============================================================
def page_edit_asset():
    aid = st.session_state.get('edit_asset_id')
    if not aid:
        go_to('assets')
        return
    r = db_select("asset", filters={"id": aid})
    if not r:
        st.error("Not found!")
        return
    a = r[0]

    st.markdown(f"## ✏️ Edit Asset: {a.get('asset_code', '')}")

    cats = db_select("asset_category", filters={"is_active": True}, order="name")
    cat_opts = {c['name']: c for c in cats}
    cat_id_map = {c['id']: c['name'] for c in cats}
    current_cat = cat_id_map.get(a.get('category_id'), '')
    cat_idx = list(cat_opts.keys()).index(current_cat) if current_cat in cat_opts else 0

    with st.form("edit_asset_form"):
        st.text_input("Asset Code", value=a.get('asset_code', ''), disabled=True)

        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Asset Name *", value=a['name'])
            sel_cat_name = st.selectbox("Category *", list(cat_opts.keys()), index=cat_idx)
            quantity = st.number_input("Quantity", value=int(a.get('quantity', 1)), min_value=1)
            purchase_val = st.number_input("Purchase Value (₹)", value=float(a.get('purchase_value', 0) or 0), step=100.0)
            pd_val = None
            if a.get('purchase_date'):
                try:
                    pd_val = datetime.strptime(str(a['purchase_date'])[:10], '%Y-%m-%d').date()
                except Exception:
                    pass
            purchase_date = st.date_input("Purchase Date", value=pd_val, format="DD/MM/YYYY")

        with c2:
            location = st.text_input("Location *", value=a.get('location') or '')
            ci = ASSET_CONDITIONS.index(a['condition']) if a.get('condition') in ASSET_CONDITIONS else 0
            condition = st.selectbox("Condition", ASSET_CONDITIONS, index=ci)
            supplier = st.text_input("Supplier/Donor", value=a.get('supplier_donor') or '')
            wd_val = None
            if a.get('warranty_expiry'):
                try:
                    wd_val = datetime.strptime(str(a['warranty_expiry'])[:10], '%Y-%m-%d').date()
                except Exception:
                    pass
            warranty_date = st.date_input("Warranty Expiry", value=wd_val, format="DD/MM/YYYY")
            serial_no = st.text_input("Serial No", value=a.get('serial_number') or '')

        description = st.text_area("Description", value=a.get('description') or '', height=80)

        if st.form_submit_button("💾 Update Asset", use_container_width=True):
            if not name.strip():
                st.error("Name required!")
            else:
                cat = cat_opts[sel_cat_name]
                changes = []
                if name.strip() != a['name']:
                    changes.append(f"Name: {a['name']} -> {name.strip()}")
                if condition != a.get('condition'):
                    changes.append(f"Condition: {a.get('condition')} -> {condition}")
                if location != (a.get('location') or ''):
                    changes.append(f"Location: {a.get('location') or '-'} -> {location}")

                db_update("asset", {
                    "name": name.strip(),
                    "description": description or None,
                    "category_id": cat['id'],
                    "location": location or None,
                    "condition": condition,
                    "quantity": quantity,
                    "purchase_value": purchase_val,
                    "purchase_date": purchase_date.isoformat() if purchase_date else None,
                    "supplier_donor": supplier or None,
                    "warranty_expiry": warranty_date.isoformat() if warranty_date else None,
                    "serial_number": serial_no or None,
                }, "id", aid)

                if changes:
                    db_insert("asset_audit_log", {
                        "asset_id": aid,
                        "action": "UPDATED",
                        "details": "; ".join(changes),
                        "performed_by": st.session_state['user_id'],
                        "performed_at": datetime.now().isoformat()
                    })

                st.success("Updated! ✅")
                go_to('view_asset', view_asset_id=aid)

    if st.button("⬅️ Back"):
        go_to('assets')


# ============================================================
# ASSET REPORTS
# ============================================================
def page_asset_reports():
    st.markdown("## 📊 Asset Reports & Inventory Tracking")

    cats = db_select("asset_category", filters={"is_active": True}, order="name")
    cat_map = {c['id']: c['name'] for c in cats}
    all_assets = db_select("asset", filters={"is_active": True})

    total_count = len(all_assets)
    total_value = sum(float(a.get('purchase_value', 0) or 0) for a in all_assets)
    total_qty = sum(int(a.get('quantity', 1) or 1) for a in all_assets)

    sc1, sc2, sc3, sc4 = st.columns(4)
    with sc1:
        st.markdown(f'<div class="stat-card assets"><h4>📦 Total Assets</h4><h2>{total_count}</h2></div>', unsafe_allow_html=True)
    with sc2:
        st.markdown(f'<div class="stat-card asset-value"><h4>💎 Total Value</h4><h2>₹{total_value:,.0f}</h2></div>', unsafe_allow_html=True)
    with sc3:
        st.markdown(f'<div class="stat-card devotees"><h4>📊 Total Quantity</h4><h2>{total_qty}</h2></div>', unsafe_allow_html=True)
    with sc4:
        st.markdown(f'<div class="stat-card bills"><h4>🏷️ Categories</h4><h2>{len(cats)}</h2></div>', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏷️ By Category", "📍 By Location", "🔧 By Condition",
        "📋 Full Inventory", "📜 Audit Log"
    ])

    with tab1:
        st.markdown("### 🏷️ Assets by Category")
        cat_data = {}
        for a in all_assets:
            cn = cat_map.get(a.get('category_id'), 'Uncategorized')
            if cn not in cat_data:
                cat_data[cn] = {'count': 0, 'quantity': 0, 'value': 0}
            cat_data[cn]['count'] += 1
            cat_data[cn]['quantity'] += int(a.get('quantity', 1) or 1)
            cat_data[cn]['value'] += float(a.get('purchase_value', 0) or 0)
        if cat_data:
            import pandas as pd
            cdf = pd.DataFrame([
                {'Category': k, 'Items': v['count'], 'Total Qty': v['quantity'],
                 'Total Value': f"₹{v['value']:,.2f}",
                 'Avg Value': f"₹{v['value'] / v['count']:,.2f}" if v['count'] > 0 else '₹0'}
                for k, v in sorted(cat_data.items(), key=lambda x: -x[1]['value'])
            ])
            st.dataframe(cdf, use_container_width=True, hide_index=True)
            chart_data = pd.DataFrame({
                'Category': list(cat_data.keys()),
                'Value': [v['value'] for v in cat_data.values()]
            }).set_index('Category')
            st.bar_chart(chart_data)

    with tab2:
        st.markdown("### 📍 Assets by Location")
        loc_data = {}
        for a in all_assets:
            loc = a.get('location') or 'Unassigned'
            if loc not in loc_data:
                loc_data[loc] = {'count': 0, 'quantity': 0, 'value': 0}
            loc_data[loc]['count'] += 1
            loc_data[loc]['quantity'] += int(a.get('quantity', 1) or 1)
            loc_data[loc]['value'] += float(a.get('purchase_value', 0) or 0)
        if loc_data:
            import pandas as pd
            ldf = pd.DataFrame([
                {'Location': k, 'Items': v['count'], 'Total Qty': v['quantity'],
                 'Total Value': f"₹{v['value']:,.2f}"}
                for k, v in sorted(loc_data.items(), key=lambda x: -x[1]['count'])
            ])
            st.dataframe(ldf, use_container_width=True, hide_index=True)

    with tab3:
        st.markdown("### 🔧 Assets by Condition")
        cond_data = {}
        for a in all_assets:
            c = a.get('condition') or 'Unknown'
            if c not in cond_data:
                cond_data[c] = {'count': 0, 'value': 0}
            cond_data[c]['count'] += 1
            cond_data[c]['value'] += float(a.get('purchase_value', 0) or 0)
        if cond_data:
            import pandas as pd
            codf = pd.DataFrame([
                {'Condition': k, 'Count': v['count'], 'Value': f"₹{v['value']:,.2f}",
                 '% of Total': f"{v['count'] / total_count * 100:.1f}%" if total_count > 0 else '0%'}
                for k, v in sorted(cond_data.items(), key=lambda x: -x[1]['count'])
            ])
            st.dataframe(codf, use_container_width=True, hide_index=True)

        attention = [a for a in all_assets if a.get('condition') in ['Poor', 'Damaged', 'Under Repair']]
        if attention:
            st.markdown("#### ⚠️ Assets Needing Attention")
            for a in attention:
                cn = cat_map.get(a.get('category_id'), 'N/A')
                st.warning(f"**{a['asset_code']}** — {a['name']} | {cn} | 📍 {a.get('location', '-')} | Condition: {a.get('condition')}")

        st.markdown("#### ⏰ Warranty Expiring Soon (Next 90 days)")
        cutoff = (date.today() + timedelta(days=90)).isoformat()
        today_iso = date.today().isoformat()
        expiring = [a for a in all_assets
                    if a.get('warranty_expiry')
                    and today_iso <= str(a['warranty_expiry'])[:10] <= cutoff]
        if expiring:
            for a in expiring:
                st.info(f"**{a['asset_code']}** — {a['name']} | Warranty: {str(a['warranty_expiry'])[:10]}")
        else:
            st.success("No warranties expiring in the next 90 days!")

    with tab4:
        st.markdown("### 📋 Complete Asset Inventory")
        if all_assets:
            import pandas as pd
            for a in all_assets:
                a['category_name'] = cat_map.get(a.get('category_id'), 'N/A')
            df = pd.DataFrame(all_assets)
            cols = ['asset_code', 'name', 'category_name', 'location', 'condition',
                    'quantity', 'purchase_value', 'purchase_date', 'supplier_donor']
            available_cols = [c for c in cols if c in df.columns]
            display_df = df[available_cols].copy()
            if 'purchase_value' in display_df.columns:
                display_df['purchase_value'] = display_df['purchase_value'].apply(
                    lambda x: f"₹{float(x or 0):,.2f}")
            if 'purchase_date' in display_df.columns:
                display_df['purchase_date'] = display_df['purchase_date'].apply(
                    lambda x: str(x)[:10] if x else '-')
            display_df.columns = [c.replace('_', ' ').title() for c in display_df.columns]
            st.dataframe(display_df, use_container_width=True, hide_index=True)

            csv = display_df.to_csv(index=False)
            st.download_button(
                "📥 Download Full Inventory (CSV)",
                data=csv,
                file_name=f"temple_asset_inventory_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

            report_html = f"""<!DOCTYPE html>
            <html><head><title>Asset Inventory Report - {TEMPLE_NAME}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #8B0000; text-align: center; }}
                h3 {{ color: #DC143C; text-align: center; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th {{ background: #8B0000; color: #FFD700; padding: 10px; text-align: left; }}
                td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
                tr:hover {{ background: #FFF8DC; }}
                .summary {{ background: #f8f9fa; padding: 15px; border-radius: 10px; margin: 15px 0; }}
                .footer {{ text-align: center; margin-top: 30px; color: #888; font-size: 0.8em; }}
            </style></head><body>
            <h1>{TEMPLE_NAME}</h1>
            <h3>{TEMPLE_TRUST}</h3>
            <p style="text-align:center;color:#666;">{TEMPLE_ADDRESS_LINE3}</p>
            <h2 style="text-align:center;">Asset Inventory Report</h2>
            <p style="text-align:center;">Generated: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
            <div class="summary">
                <b>Total Assets:</b> {total_count} |
                <b>Total Value:</b> ₹{total_value:,.2f} |
                <b>Total Quantity:</b> {total_qty} |
                <b>Categories:</b> {len(cats)}
            </div>
            <table><thead><tr>
                <th>Code</th><th>Name</th><th>Category</th><th>Location</th>
                <th>Condition</th><th>Qty</th><th>Value</th><th>Purchase Date</th>
            </tr></thead><tbody>"""
            for a in sorted(all_assets, key=lambda x: x.get('asset_code', '')):
                report_html += f"""<tr>
                    <td><code>{a.get('asset_code', '-')}</code></td>
                    <td>{a['name']}</td>
                    <td>{cat_map.get(a.get('category_id'), '-')}</td>
                    <td>{a.get('location') or '-'}</td>
                    <td>{a.get('condition') or '-'}</td>
                    <td>{a.get('quantity', 1)}</td>
                    <td>₹{float(a.get('purchase_value', 0) or 0):,.2f}</td>
                    <td>{str(a.get('purchase_date') or '-')[:10]}</td></tr>"""
            report_html += f"""</tbody></table>
            <div class="footer">{TEMPLE_FULL_ADDRESS}<br>Report generated by Temple Management System</div>
            </body></html>"""
            st.download_button(
                "📥 Download Printable Report (HTML)",
                data=report_html,
                file_name=f"asset_report_{datetime.now().strftime('%Y%m%d')}.html",
                mime="text/html"
            )
        else:
            st.info("No assets registered yet.")

    with tab5:
        st.markdown("### 📜 Recent Audit Activity")
        logs = db_select("asset_audit_log", order="-performed_at", limit=50)
        if logs:
            import pandas as pd
            for log in logs:
                if log.get('asset_id'):
                    ast = db_select("asset", "asset_code,name", filters={"id": log['asset_id']})
                    log['asset'] = f"{ast[0]['asset_code']} - {ast[0]['name']}" if ast else '-'
                else:
                    log['asset'] = '-'
                if log.get('performed_by'):
                    u = db_select("users", "full_name", filters={"id": log['performed_by']})
                    log['user'] = u[0]['full_name'] if u else '-'
                else:
                    log['user'] = '-'
            df = pd.DataFrame(logs)
            df['Date'] = df['performed_at'].apply(lambda x: str(x)[:19] if x else '-')
            st.dataframe(
                df[['Date', 'asset', 'action', 'details', 'user']].rename(
                    columns={'asset': 'Asset', 'action': 'Action', 'details': 'Details', 'user': 'By'}
                ),
                use_container_width=True, hide_index=True
            )
        else:
            st.info("No audit logs yet")


# ============================================================
# SAMAYA VAKUPPU
# ============================================================
def page_samaya():
    st.markdown("## 🎓 Samaya Vakuppu")
    if st.button("➕ Add"):
        go_to('add_samaya', edit_samaya_id=None)
    for s in db_select("samaya_vakuppu", order="student_name"):
        c1, c2, c3 = st.columns([3, 3, 1])
        with c1:
            st.write(f"**{s['student_name']}** | Parent: {s.get('father_mother_name') or '-'}")
        with c2:
            st.write(f"Bond: {s.get('bond_no') or '-'} | Bank: {s.get('bond_issuing_bank') or '-'}")
        with c3:
            if st.button("✏️", key=f"es{s['id']}"):
                go_to('add_samaya', edit_samaya_id=s['id'])
            if st.button("🗑", key=f"ds{s['id']}"):
                db_delete("samaya_vakuppu", "id", s['id'])
                st.rerun()
        st.markdown("---")


def page_add_samaya():
    eid = st.session_state.get('edit_samaya_id')
    s = None
    if eid:
        r = db_select("samaya_vakuppu", filters={"id": eid})
        s = r[0] if r else None

    st.markdown(f"## {'✏️ Edit' if s else '➕ Add'} Student")
    with st.form("sf"):
        c1, c2 = st.columns(2)
        with c1:
            nm = st.text_input("Name *", value=s['student_name'] if s else '')
            par = st.text_input("Parent", value=s.get('father_mother_name') or '' if s else '')
            bn = st.text_input("Bond No", value=s.get('bond_no') or '' if s else '')
        with c2:
            bk = st.text_input("Bank", value=s.get('bond_issuing_bank') or '' if s else '')
            br = st.text_input("Branch", value=s.get('branch_of_bank') or '' if s else '')
        addr = st.text_area("Address", value=s.get('address') or '' if s else '')
        if st.form_submit_button("💾 Save"):
            if nm.strip():
                data = {"student_name": nm, "father_mother_name": par or None,
                        "bond_no": bn or None, "bond_issuing_bank": bk or None,
                        "branch_of_bank": br or None, "address": addr or None}
                if eid and s:
                    db_update("samaya_vakuppu", data, "id", eid)
                else:
                    db_insert("samaya_vakuppu", data)
                st.success("Saved! ✅")
                go_to('samaya')
    if st.button("⬅️ Back"):
        go_to('samaya')


# ============================================================
# MANDAPAM
# ============================================================
def page_mandapam():
    st.markdown("## 🏛️ Thirumana Mandapam")
    if st.button("➕ Add"):
        go_to('add_mandapam', edit_mandapam_id=None)
    for m in db_select("thirumana_mandapam", order="name"):
        c1, c2, c3 = st.columns([3, 3, 1])
        with c1:
            st.write(f"**{m['name']}** | Bond: {m.get('bond_no') or '-'}")
        with c2:
            st.write(f"₹{float(m.get('amount', 0)):,.2f} | Bonds: {m.get('no_of_bond', 1)}")
        with c3:
            if st.button("✏️", key=f"em{m['id']}"):
                go_to('add_mandapam', edit_mandapam_id=m['id'])
            if st.button("🗑", key=f"dm{m['id']}"):
                db_delete("thirumana_mandapam", "id", m['id'])
                st.rerun()
        st.markdown("---")


def page_add_mandapam():
    eid = st.session_state.get('edit_mandapam_id')
    m = None
    if eid:
        r = db_select("thirumana_mandapam", filters={"id": eid})
        m = r[0] if r else None

    st.markdown(f"## {'✏️ Edit' if m else '➕ Add'} Record")
    with st.form("mf"):
        c1, c2 = st.columns(2)
        with c1:
            nm = st.text_input("Name *", value=m['name'] if m else '')
            bn = st.text_input("Bond No", value=m.get('bond_no') or '' if m else '')
        with c2:
            amt = st.number_input("Amount", value=float(m.get('amount', 0)) if m else 0.0, step=100.0)
            nb = st.number_input("Bonds", value=int(m.get('no_of_bond', 1)) if m else 1, min_value=1)
        addr = st.text_area("Address", value=m.get('address') or '' if m else '')
        if st.form_submit_button("💾 Save"):
            if nm.strip():
                data = {"name": nm, "bond_no": bn or None, "amount": amt,
                        "no_of_bond": nb, "address": addr or None}
                if eid and m:
                    db_update("thirumana_mandapam", data, "id", eid)
                else:
                    db_insert("thirumana_mandapam", data)
                st.success("Saved! ✅")
                go_to('mandapam')
    if st.button("⬅️ Back"):
        go_to('mandapam')


# ============================================================
# DAILY POOJA
# ============================================================
def page_daily_pooja():
    st.markdown("## 🙏 Daily Pooja")
    for p in db_select("daily_pooja", filters={"is_active": True}, order="pooja_time"):
        c1, c2, c3 = st.columns([3, 3, 1])
        with c1:
            st.write(f"**{p['pooja_name']}** — {p.get('pooja_time') or 'TBD'}")
        with c2:
            st.write(p.get('description') or '-')
        with c3:
            if st.button("🗑", key=f"dp{p['id']}"):
                db_update("daily_pooja", {"is_active": False}, "id", p['id'])
                st.rerun()

    with st.form("adp"):
        c1, c2, c3 = st.columns(3)
        with c1:
            pn = st.text_input("Name *")
        with c2:
            pt = st.text_input("Time (e.g. 6:00 AM)")
        with c3:
            pdesc = st.text_input("Description")
        if st.form_submit_button("➕ Add"):
            if pn.strip():
                db_insert("daily_pooja", {
                    "pooja_name": pn, "pooja_time": pt or None,
                    "description": pdesc or None, "is_active": True
                })
                st.rerun()


# ============================================================
# SETTINGS
# ============================================================
def page_settings():
    st.markdown("## ⚙️ Settings")
    cl, cr = st.columns(2)

    with cl:
        st.markdown("### 🕉️ Pooja Types")
        for p in db_select("pooja_type", filters={"is_active": True}, order="name"):
            c1, c2, c3 = st.columns([3, 1.5, 1])
            with c1:
                st.write(p['name'])
            with c2:
                st.write(f"₹{p['amount']}")
            with c3:
                if st.button("🗑", key=f"dpt{p['id']}"):
                    db_update("pooja_type", {"is_active": False}, "id", p['id'])
                    st.rerun()
        with st.form("apt"):
            pn = st.text_input("Name *", key="npn")
            pa = st.number_input("Amount", value=0.0, step=10.0, key="npa")
            if st.form_submit_button("➕ Add"):
                if pn.strip():
                    db_insert("pooja_type", {"name": pn, "amount": pa, "is_active": True})
                    st.rerun()

    with cr:
        st.markdown("### 🏷️ Expense Types")
        for e in db_select("expense_type", filters={"is_active": True}, order="name"):
            c1, c2 = st.columns([4, 1])
            with c1:
                st.write(e['name'])
            with c2:
                if st.button("🗑", key=f"det{e['id']}"):
                    db_update("expense_type", {"is_active": False}, "id", e['id'])
                    st.rerun()
        with st.form("aet"):
            en = st.text_input("Name *", key="nen")
            if st.form_submit_button("➕ Add"):
                if en.strip():
                    db_insert("expense_type", {"name": en, "is_active": True})
                    st.rerun()


# ============================================================
# USER MANAGEMENT
# ============================================================
def page_users():
    if not is_admin():
        st.error("Admin only!")
        return
    st.markdown("## 👤 Users")
    for u in db_select("users", order="id"):
        c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
        with c1:
            st.write(f"**{u['username']}** ({u.get('full_name') or '-'})")
        with c2:
            st.write(f"{'🔴 Admin' if u['role'] == 'admin' else '🔵 User'}")
        with c3:
            st.write("✅" if u['is_active_user'] else "⛔")
        with c4:
            if u['id'] != st.session_state['user_id']:
                if st.button("Toggle", key=f"tu{u['id']}"):
                    db_update("users", {"is_active_user": not u['is_active_user']}, "id", u['id'])
                    st.rerun()
        st.markdown("---")

    with st.form("au"):
        st.markdown("### ➕ Add User")
        c1, c2 = st.columns(2)
        with c1:
            un = st.text_input("Username *")
            fn = st.text_input("Full Name")
        with c2:
            pw = st.text_input("Password *", type="password")
            rl = st.selectbox("Role", ['user', 'admin'])
        if st.form_submit_button("👤 Create"):
            if un and pw:
                existing = db_select("users", filters={"username": un})
                if existing:
                    st.error("Username exists!")
                else:
                    db_insert("users", {
                        "username": un,
                        "password_hash": generate_password_hash(pw),
                        "full_name": fn or None,
                        "role": rl,
                        "is_active_user": True
                    })
                    st.success("Created! ✅")
                    st.rerun()


# ============================================================
# DELETED BILLS
# ============================================================
def page_deleted_bills():
    if not is_admin():
        st.error("Admin only!")
        return
    st.markdown("## 🗑️ Deleted Bills")
    del_bills = db_select("bill", filters={"is_deleted": True}, order="-deleted_at")
    if del_bills:
        import pandas as pd
        for b in del_bills:
            if b.get('deleted_by'):
                u = db_select("users", "full_name", filters={"id": b['deleted_by']})
                b['del_by'] = u[0]['full_name'] if u else '-'
            else:
                b['del_by'] = '-'
        df = pd.DataFrame(del_bills)
        df['Date'] = df['bill_date'].apply(lambda x: str(x)[:10])
        df['Amount'] = df['amount'].apply(lambda x: f"₹{float(x or 0):,.2f}")
        st.dataframe(df[['bill_number', 'Date', 'Amount', 'del_by', 'delete_reason']].rename(
            columns={'bill_number': 'Bill', 'del_by': 'Deleted By', 'delete_reason': 'Reason'}),
            use_container_width=True, hide_index=True)
    else:
        st.info("No deleted bills")


# ============================================================
# MAIN
# ============================================================
def main():
    init_session()
    load_css()

    if not st.session_state['logged_in']:
        login_page()
        return

    sidebar()

    pages = {
        'dashboard': page_dashboard,
        'devotees': page_devotees,
        'add_devotee': page_add_devotee,
        'view_devotee': page_view_devotee,
        'billing': page_billing,
        'new_bill': page_new_bill,
        'view_bill': page_view_bill,
        'expenses': page_expenses,
        'reports': page_reports,
        'assets': page_assets,
        'view_asset': page_view_asset,
        'edit_asset': page_edit_asset,
        'asset_reports': page_asset_reports,
        'samaya': page_samaya,
        'add_samaya': page_add_samaya,
        'mandapam': page_mandapam,
        'add_mandapam': page_add_mandapam,
        'daily_pooja': page_daily_pooja,
        'settings': page_settings,
        'users': page_users,
        'deleted_bills': page_deleted_bills,
    }

    page = st.session_state.get('page', 'dashboard')
    pages.get(page, page_dashboard)()


if __name__ == "__main__":
    main()
