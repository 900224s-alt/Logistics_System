import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="物流退貨點收系統", layout="wide")

# 強制指向同一個資料庫檔案
DB_PATH = 'return_system.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT, password TEXT, role TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS return_batches (batch_id TEXT PRIMARY KEY, channel_name TEXT, create_date TEXT, status TEXT, approved_by TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS return_items (batch_id TEXT, barcode TEXT, return_type TEXT, expiry_date TEXT, quantity INTEGER, quality_status TEXT, damage_reason TEXT, operator TEXT)''')
    conn.commit(); conn.close()

init_db()

# 狀態管理
if 'logged_in' not in st.session_state: 
    st.session_state.update({'logged_in': False, 'username': "", 'is_admin': False})

st.title("📦 物流退貨點收系統")

if not st.session_state['logged_in']:
    name = st.text_input("姓名")
    pwd = st.text_input("密碼", type="password")
    if st.button("登入"):
        conn = sqlite3.connect(DB_PATH)
        user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (name, pwd)).fetchone()
        if user:
            st.session_state.update({'logged_in': True, 'username': name, 'is_admin': (name == "余宸緯")})
            conn.close(); st.rerun()
        conn.close()
else:
    tabs = st.tabs(["📦 點收", "🔍 歷史", "🔔 管理"])
    
    with tabs[0]: # 點收區
        chan = st.selectbox("通路", ["MOMO", "寶雅", "康是美", "屈臣氏"])
        if st.button("鎖定並開始"):
            bid = f"Back{datetime.now().strftime('%Y%m%d%H%M%S')}"
            conn = sqlite3.connect(DB_PATH)
            conn.execute("INSERT INTO return_batches VALUES (?, ?, ?, '作業中', '')", (bid, chan, datetime.now().strftime("%Y-%m-%d"),))
            st.session_state['bid'] = bid
            conn.commit(); conn.close()
        
        if 'bid' in st.session_state:
            st.write(f"當前批號：{st.session_state['bid']}")
            bc = st.text_input("條碼")
            if st.button("儲存"):
                conn = sqlite3.connect(DB_PATH)
                conn.execute('INSERT INTO return_items VALUES (?,?,?,?,?,?,?,?)', (st.session_state['bid'], bc, "箱出", "", 1, "良品", "", st.session_state['username']))
                conn.commit(); conn.close()

    with tabs[1]: # 歷史紀錄 (強制分開讀取，避免衝突)
        conn = sqlite3.connect(DB_PATH)
        # 直接讀取 return_items，不進行任何複雜的 JOIN
        df = pd.read_sql_query("SELECT * FROM return_items", conn)
        conn.close()
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("資料庫中目前沒有任何點收紀錄。")

    with tabs[2]: # 管理區
        if st.session_state['is_admin']:
            conn = sqlite3.connect(DB_PATH)
            pending = pd.read_sql_query("SELECT * FROM return_batches", conn)
            st.dataframe(pending, use_container_width=True)
            conn.close()
        else:
            st.error("管理區僅限管理者訪問")
