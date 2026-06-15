import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# 設定頁面
st.set_page_config(page_title="物流退貨點收系統", layout="centered")

# 💡 【核心權限設定】
ORIGINAL_ADMIN = "余宸緯"

# 資料庫初始化 (確保所有欄位都在)
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

# --- 登入與註冊邏輯 (完整保留) ---
if not st.session_state['logged_in']:
    tab1, tab2 = st.tabs(["👤 帳號登入", "📝 新人員註冊"])
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
            else: st.error("帳號或密碼錯誤")
    with tab2:
        reg_name = st.text_input("註冊姓名").strip()
        reg_pwd = st.text_input("設定密碼", type="password")
        if st.button("建立帳號"):
            if reg_name and reg_pwd:
                conn = get_db_connection()
                try:
                    conn.execute('INSERT INTO users VALUES (?, ?, ?)', (reg_name, reg_pwd, "一般用戶"))
                    conn.commit()
                    st.success("註冊成功，請前往登入")
                except: st.error("姓名已被註冊")
                conn.close()
else:
    # --- 主系統 ---
    st.sidebar.write(f"作業員：**{st.session_state['username']}**")
    if st.sidebar.button("登出"):
        st.session_state.clear()
        st.rerun()

    tabs = st.tabs(["📦 點收作業", "🔍 歷史紀錄"])
    
    with tabs[0]:
        if not st.session_state['current_channel']:
            selected = st.selectbox("選擇通路", ["請選擇...", "MOMO", "寶雅", "康是美", "屈臣氏"])
            if st.button("開始作業"):
                if selected != "請選擇...":
                    st.session_state['current_channel'] = selected
                    st.session_state['current_batch_id'] = f"{selected}_{datetime.now().strftime('%Y%m%d')}"
                    st.rerun()
        else:
            st.write(f"通路：**{st.session_state['current_channel']}** | 批號：**{st.session_state['current_batch_id']}**")
            
            # 條碼輸入區
            barcode = st.text_input("請刷取或輸入商品條碼")
            
            # 設定退貨資料
            ret_type = st.radio("退貨形態", ["箱出", "散出"], horizontal=True)
            exp, qty, quality, reason = "", 1, "良品", ""
            
            if ret_type == "散出":
                exp = st.text_input("有效期限")
                qty = st.number_input("數量", min_value=1, value=1)
                quality = st.radio("貨況", ["良品", "不良品"], horizontal=True)
                if quality == "不良品": reason = st.text_input("異常原因 (手動輸入)")
            
            if st.button("💾 儲存並繼續"):
                if not barcode: st.error("請刷條碼！")
                else:
                    conn = get_db_connection()
                    conn.execute('''INSERT INTO return_items 
                                    (batch_id, barcode, return_type, expiry_date, quantity, quality_status, damage_reason, operator) 
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                                 (st.session_state['current_batch_id'], barcode, ret_type, exp, qty, quality, reason, st.session_state['username']))
                    conn.commit()
                    conn.close()
                    st.success(f"已記錄條碼：{barcode}")
                    st.rerun()
            
            if st.button("🚪 結束本批次"):
                st.session_state['current_channel'] = ""
                st.rerun()

    with tabs[1]:
        conn = get_db_connection()
        df = pd.read_sql_query("SELECT * FROM return_items", conn)
        conn.close()
        st.dataframe(df)
