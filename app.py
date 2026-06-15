import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# 設定頁面
st.set_page_config(page_title="物流退貨點收系統", layout="centered")

# 💡 【核心權限設定】這裡必須定義您的名字，確保管理者權限正確
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

# Session 初始化
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'username' not in st.session_state: st.session_state['username'] = ""
if 'is_admin' not in st.session_state: st.session_state['is_admin'] = False
if 'current_channel' not in st.session_state: st.session_state['current_channel'] = ""
if 'current_batch_id' not in st.session_state: st.session_state['current_batch_id'] = ""

st.title("📦 物流退貨點收系統")

# --- 登入邏輯 ---
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
            # 權限判定
            if name == ORIGINAL_ADMIN or user['role'] == "管理者":
                st.session_state['is_admin'] = True
            st.rerun()
        else: st.error("帳號或密碼錯誤")
else:
    # --- 主系統邏輯 ---
    st.sidebar.write(f"作業員：**{st.session_state['username']}**")
    st.sidebar.write(f"權限：**{'管理者' if st.session_state['is_admin'] else '一般用戶'}**")
    if st.sidebar.button("登出"):
        st.session_state['logged_in'] = False
        st.session_state['current_channel'] = ""
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
            st.write(f"當前通路：**{st.session_state['current_channel']}** | 批號：**{st.session_state['current_batch_id']}**")
            
            # 純淨輸入區 (絕不報錯)
            barcode = st.text_input("請刷取或輸入商品條碼")
            
            ret_type = st.radio("退貨形態", ["箱出", "散出"], horizontal=True)
            
            exp, qty, quality, reason = "", 1, "良品", ""
            if ret_type == "散出":
                exp = st.text_input("有效期限")
                qty = st.number_input("數量", min_value=1, value=1)
                quality = st.radio("貨況", ["良品", "不良品"], horizontal=True)
                if quality == "不良品":
                    reason = st.text_input("異常原因 (手動輸入)")
            
            if st.button("💾 儲存並繼續"):
                if not barcode:
                    st.error("請務必刷取或輸入條碼！")
                else:
                    conn = get_db_connection()
                    conn.execute('''INSERT INTO return_items 
                                    (batch_id, barcode, return_type, expiry_date, quantity, quality_status, damage_reason, operator) 
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                                 (st.session_state['current_batch_id'], barcode, ret_type, exp, qty, quality, reason, st.session_state['username']))
                    conn.commit()
                    conn.close()
                    st.success(f"成功記錄：{barcode}")
                    st.rerun()
            
            if st.button("🚪 結束本批次作業"):
                st.session_state['current_channel'] = ""
                st.rerun()

    with tabs[1]:
        st.subheader("歷史紀錄")
        conn = get_db_connection()
        df = pd.read_sql_query("SELECT * FROM return_items", conn)
        conn.close()
        st.dataframe(df)
