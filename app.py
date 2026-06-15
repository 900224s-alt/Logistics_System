import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="物流退貨點收系統", layout="centered")

# 管理者定義
ORIGINAL_ADMIN = "余宸緯"

# 初始化資料庫
def init_db():
    conn = sqlite3.connect('return_system.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS return_batches (batch_id TEXT PRIMARY KEY, channel_name TEXT, status TEXT)')
    cursor.execute('''CREATE TABLE IF NOT EXISTS return_items 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, batch_id TEXT, barcode TEXT, 
                       return_type TEXT, expiry_date TEXT, quantity INTEGER, quality_status TEXT, 
                       damage_reason TEXT, operator TEXT)''')
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    conn = sqlite3.connect('return_system.db')
    conn.row_factory = sqlite3.Row
    return conn

# 初始化 Session
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'username' not in st.session_state: st.session_state['username'] = ""
if 'is_admin' not in st.session_state: st.session_state['is_admin'] = False

st.title("📦 物流退貨點收系統")

# --- 登入頁面 ---
if not st.session_state['logged_in']:
    tab1, tab2 = st.tabs(["👤 登入", "📝 註冊"])
    with tab1:
        name = st.text_input("姓名").strip()
        pwd = st.text_input("密碼", type="password")
        if st.button("登入"):
            conn = get_db_connection()
            user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (name, pwd)).fetchone()
            conn.close()
            if user:
                st.session_state['logged_in'] = True
                st.session_state['username'] = name
                if name == ORIGINAL_ADMIN or user['role'] == "管理者": st.session_state['is_admin'] = True
                st.rerun()
            else: st.error("錯誤")
    with tab2:
        reg_name = st.text_input("註冊姓名").strip()
        reg_pwd = st.text_input("設定密碼", type="password")
        if st.button("註冊"):
            conn = get_db_connection()
            try:
                conn.execute('INSERT INTO users VALUES (?, ?, ?)', (reg_name, reg_pwd, "一般用戶"))
                conn.commit()
                st.success("註冊成功")
            except: st.error("姓名已存在")
            conn.close()
else:
    # --- 主系統 ---
    st.sidebar.write(f"作業員：{st.session_state['username']}")
    if st.session_state['is_admin']: st.sidebar.write("👑 管理者權限")
    if st.sidebar.button("登出"): st.session_state.clear(); st.rerun()

    # 所有分頁 (包含主管審核與權限維護)
    tabs_labels = ["📦 點收", "🔍 歷史"]
    if st.session_state['is_admin']: tabs_labels.extend(["🔔 審核", "👥 維護"])
    tabs = st.tabs(tabs_labels)

    # 1. 點收作業
    with tabs[0]:
        if 'channel' not in st.session_state: st.session_state['channel'] = ""
        if not st.session_state['channel']:
            selected = st.selectbox("通路", ["請選擇...", "MOMO", "寶雅", "康是美", "屈臣氏"])
            if st.button("開始作業"):
                if selected != "請選擇...": st.session_state['channel'] = selected; st.rerun()
        else:
            st.write(f"當前通路：{st.session_state['channel']}")
            # 條碼輸入區 (改用原生相機輔助與手動輸入，完全排除錯誤)
            barcode = st.text_input("請刷條碼或手動輸入")
            st.camera_input("拍照輔助辨識")
            
            ret = st.radio("類型", ["箱出", "散出"], horizontal=True)
            exp = st.text_input("有效期限") if ret == "散出" else ""
            qty = st.number_input("數量", value=1) if ret == "散出" else 1
            quality = st.radio("貨況", ["良品", "不良品"], horizontal=True) if ret == "散出" else "良品"
            reason = st.text_input("異常原因") if quality == "不良品" else ""
            
            if st.button("儲存"):
                conn = get_db_connection()
                conn.execute('INSERT INTO return_items (barcode, return_type, expiry_date, quantity, quality_status, damage_reason, operator) VALUES (?,?,?,?,?,?,?,?)',
                             (barcode, ret, exp, qty, quality, reason, st.session_state['username']))
                conn.commit()
                conn.close()
                st.success("儲存成功")
    
    # 2. 歷史紀錄
    with tabs[1]:
        conn = get_db_connection()
        st.dataframe(pd.read_sql_query("SELECT * FROM return_items", conn))
        conn.close()

    # 3. 管理者功能
    if st.session_state['is_admin']:
        with tabs[2]: st.write("審核功能頁面...")
        with tabs[3]: st.write("人員維護功能頁面...")
