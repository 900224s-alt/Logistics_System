import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

# --- 台灣時間 ---
def get_tw_now():
    return datetime.utcnow() + timedelta(hours=8)

# --- CSS ---
st.markdown("""
<style>
div.stButton > button[kind="primary"] {
    background-color: #8da3b4 !important;
    border: none !important;
    color: white !important;
}
div.stButton > button#back-btn {
    background-color: #d4c4a8 !important;
    border: none !important;
    color: white !important;
}
div.stButton > button#close-btn {
    background-color: #c48b8b !important;
    border: none !important;
    color: white !important;
}
</style>
""", unsafe_allow_html=True)

ORIGINAL_ADMIN = "余宸緯"

DAMAGE_REASONS = [
    "盒凹", "嚴重盒凹", "盒污", "劃痕", "防盜貼",
    "已過期（一個月內）", "即期（兩個月內）", "短效（半年內）",
    "效期模糊", "批號模糊", "已開封", "已開封使用", "空盒",
    "膠膜破損", "膠膜嚴重破損", "膠膜污損",
    "色差", "漸層色差", "嚴重色差",
    "霧氣", "漏液", "嚴重漏液"
]

# --- DB ---
def get_db_connection():
    conn = sqlite3.connect("return_system.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT,
        register_date TEXT,
        role TEXT
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS return_batches (
        batch_id TEXT PRIMARY KEY,
        channel TEXT,
        register_date TEXT,
        status TEXT
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS return_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        batch_id TEXT,
        barcode TEXT,
        return_type TEXT,
        expiry_date TEXT,
        quantity INTEGER,
        quality_status TEXT,
        damage_reason TEXT,
        operator TEXT,
        approval_status TEXT,
        created_at TEXT,
        remark TEXT
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS change_requests (
        req_id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER,
        action TEXT,
        old_qty INTEGER,
        new_qty INTEGER,
        new_status TEXT,
        new_expiry TEXT,
        reason TEXT,
        status TEXT
    )""")

    conn.commit()
    conn.close()


init_db()

# --- session ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = ""

st.title("📦 物流退貨系統")

# ======================================================
# 登入 / 註冊
# ======================================================
if not st.session_state.logged_in:

    tab1, tab2 = st.tabs(["登入", "註冊"])

    with tab1:
        login_name = st.text_input("姓名").strip()
        login_pwd = st.text_input("密碼", type="password")

        if st.button("登入"):
            conn = get_db_connection()
            user = conn.execute(
                "SELECT * FROM users WHERE username=? AND password=?",
                (login_name, login_pwd)
            ).fetchone()
            conn.close()

            if user:
                st.session_state.logged_in = True
                st.session_state.username = login_name
                st.session_state.is_admin = (
                    user["role"] == "管理者" or login_name == ORIGINAL_ADMIN
                )
                st.rerun()
            else:
                st.error("登入失敗")

    with tab2:
        reg_name = st.text_input("姓名").strip()
        reg_pwd = st.text_input("密碼", type="password")

        if st.button("註冊"):
            conn = get_db_connection()
            try:
                role = "管理者" if reg_name == ORIGINAL_ADMIN else "一般用戶"
                conn.execute(
                    "INSERT INTO users VALUES (?, ?, ?, ?)",
                    (reg_name, reg_pwd, get_tw_now().strftime("%Y-%m-%d %H:%M:%S"), role)
                )
                conn.commit()
                st.success("註冊成功")
            except:
                st.error("已存在")
            finally:
                conn.close()

# ======================================================
# 主系統
# ======================================================
else:

    st.sidebar.write(f"👤 {st.session_state.username}")
    st.sidebar.write(f"🎖️ {'管理者' if st.session_state.get('is_admin') else '一般用戶'}")

    if st.sidebar.button("登出"):
        st.session_state.clear()
        st.rerun()

    tabs = st.tabs(["作業", "歷史", "審核", "員工"])

    # ==================================================
    # 作業
    # ==================================================
    with tabs[0]:
        st.write("作業頁（簡化版）")

    # ==================================================
    # 歷史
    # ==================================================
    with tabs[1]:
        st.write("歷史頁（簡化版）")

    # ==================================================
    # 審核
    # ==================================================
    with tabs[2]:
        st.write("審核頁（簡化版）")

    # ==================================================
    # 員工
    # ==================================================
    with tabs[3]:
        st.write("員工頁（簡化版）")
