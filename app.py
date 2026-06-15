import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# 頁面設定
st.set_page_config(page_title="物流退貨點收系統", layout="centered")

# 權限定義
ORIGINAL_ADMIN = "余宸緯"

# 資料庫初始化
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
if 'current_channel' not in st.session_state: st.session_state['current_channel'] = ""
if 'current_batch_id' not in st.session_state: st.session_state['current_batch_id'] = ""

st.title("📦 物流退貨點收系統")

# 登入區
if not st.session_state['logged_in']:
    st.subheader("👤 系統登入")
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
        else: st.error("帳號或密碼錯誤")
else:
    # 主系統
    st.sidebar.write(f"作業員：**{st.session_state['username']}**")
    if st.sidebar.button("登出"):
        st.session_state.clear()
        st.rerun()

    tabs = st.tabs(["📦 點收作業", "🔍 歷史紀錄"])
    
    with tabs[0]:
        if not st.session_state['current_channel']:
            selected = st.selectbox("選擇退貨通路", ["請選擇...", "MOMO", "寶雅", "康是美", "屈臣氏"])
            if st.button("鎖定通路並開始作業"):
                if selected != "請選擇...":
                    st.session_state['current_channel'] = selected
                    today = datetime.now().strftime("%Y%m%d")
                    st.session_state['current_batch_id'] = f"{selected}_{today}"
                    st.rerun()
        else:
            st.write(f"通路：**{st.session_state['current_channel']}** | 批號：**{st.session_state['current_batch_id']}**")
            
            # 條碼輸入 (掃碼槍最佳化)
            barcode = st.text_input("請刷取或輸入條碼")
            
            # 使用官方相機拍照，不需第三方 HTML，最穩定
            st.info("若無掃碼槍，可點擊下方相機拍照存證")
            img = st.camera_input("拍攝條碼")
            
            # 參數設定
            ret_type = st.radio("退貨形態", ["箱出", "散出"], horizontal=True)
            exp, qty, quality, reason = "", 1, "良品", ""
            
            if ret_type == "散出":
                exp = st.text_input("有效期限")
                qty = st.number_input("數量", min_value=1, value=1)
                quality = st.radio("貨況", ["良品", "不良品"], horizontal=True)
                if quality == "不良品": reason = st.text_input("異常原因")
            
            if st.button("💾 儲存資料"):
                if not barcode: st.error("請刷條碼！")
                else:
                    conn = get_db_connection()
                    conn.execute('''INSERT INTO return_items (batch_id, barcode, return_type, expiry_date, quantity, quality_status, damage_reason, operator) 
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                                 (st.session_state['current_batch_id'], barcode, ret_type, exp, qty, quality, reason, st.session_state['username']))
                    conn.commit()
                    conn.close()
                    st.success(f"已記錄：{barcode}")
            
            if st.button("🚪 結束作業"):
                st.session_state['current_channel'] = ""
                st.rerun()

    with tabs[1]:
        conn = get_db_connection()
        df = pd.read_sql_query("SELECT * FROM return_items", conn)
        conn.close()
        st.dataframe(df)
