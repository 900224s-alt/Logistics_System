import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="物流退貨點收系統", layout="wide")

# 初始化 DB
def init_db():
    conn = sqlite3.connect('return_system.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, register_date TEXT, role TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS return_batches (batch_id TEXT PRIMARY KEY, channel_name TEXT, create_date TEXT, status TEXT, approved_by TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS return_items (id INTEGER PRIMARY KEY AUTOINCREMENT, batch_id TEXT, item_seq INTEGER, barcode TEXT, return_type TEXT, expiry_date TEXT, quantity INTEGER, quality_status TEXT, damage_reason TEXT, operator TEXT)''')
    conn.commit(); conn.close()
init_db()

def get_conn():
    conn = sqlite3.connect('return_system.db')
    conn.row_factory = sqlite3.Row
    return conn

# Session 初始化
if 'logged_in' not in st.session_state: 
    st.session_state.update({'logged_in': False, 'username': "", 'is_admin': False})

st.title("📦 物流退貨點收系統")

if not st.session_state['logged_in']:
    name = st.text_input("姓名")
    pwd = st.text_input("密碼", type="password")
    if st.button("登入"):
        conn = get_conn()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (name, pwd)).fetchone()
        if user:
            st.session_state.update({'logged_in': True, 'username': name, 'is_admin': (user['role'] == "管理者" or name == "余宸緯")})
            conn.close(); st.rerun()
        conn.close()
else:
    st.sidebar.write(f"👤 {st.session_state['username']}")
    if st.sidebar.button("登出"): st.session_state.update({'logged_in': False}); st.rerun()
    
    tabs = st.tabs(["📦 點收", "🔍 歷史", "🔔 管理"])
    
    with tabs[0]:
        env = st.radio("環境", ["正式", "測試"], horizontal=True) if st.session_state['is_admin'] else "正式"
        chan = st.selectbox("通路", ["MOMO", "寶雅", "康是美", "屈臣氏"])
        if st.button("鎖定"):
            st.session_state['bid'] = f"{'TEST' if env=='測試' else 'Back'}{datetime.now().strftime('%Y%m%d%H%M%S')}"
            conn = get_conn()
            conn.execute("INSERT INTO return_batches VALUES (?, ?, ?, '作業中', '')", (st.session_state['bid'], chan, datetime.now().strftime("%Y-%m-%d")))
            conn.commit(); conn.close(); st.rerun()
        if 'bid' in st.session_state:
            st.write(f"批號: {st.session_state['bid']}")
            bc = st.text_input("條碼")
            if st.button("儲存"):
                conn = get_conn()
                conn.execute('INSERT INTO return_items (batch_id, barcode, operator) VALUES (?,?,?)', (st.session_state['bid'], bc, st.session_state['username']))
                conn.commit(); conn.close(); st.rerun()

    with tabs[1]:
        conn = get_conn()
        # 拆解查詢：先讀取兩張表
        df_items = pd.read_sql_query("SELECT * FROM return_items", conn)
        df_batches = pd.read_sql_query("SELECT * FROM return_batches", conn)
        conn.close()
        
        if not df_items.empty and not df_batches.empty:
            # 在 Python 端手動合併，完全避開 SQL 語法錯誤
            df = pd.merge(df_items, df_batches, on='batch_id', how='left')
            # 欄位重新命名以符合您的需求
            df = df.rename(columns={'create_date': '建檔日期', 'barcode': '條碼', 'operator': '人員'})
            st.dataframe(df, use_container_width=True, hide_index=True)
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下載 CSV", data=csv, file_name="report.csv", mime="text/csv")
        else: st.info("無資料")

    with tabs[2]:
        if st.session_state['is_admin']:
            conn = get_conn()
            pending = pd.read_sql_query("SELECT * FROM return_batches", conn)
            st.dataframe(pending, use_container_width=True)
            bid = st.text_input("批號簽核")
            if st.button("簽核"):
                conn.execute("UPDATE return_batches SET status='已簽核', approved_by=? WHERE batch_id=?", (st.session_state['username'], bid))
                conn.commit(); conn.close(); st.rerun()
