import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="物流退貨點收系統", layout="wide")

# 初始化資料庫結構
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

if 'logged_in' not in st.session_state: 
    st.session_state.update({'logged_in': False, 'username': "", 'is_admin': False, 'current_channel': ""})

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
    if st.sidebar.button("登出"): st.session_state.update({'logged_in': False, 'current_channel': ""}); st.rerun()
    
    tabs = st.tabs(["📦 點收", "🔍 歷史", "🔔 管理"])
    
    with tabs[0]:
        if st.session_state['is_admin']:
            env = st.radio("環境", ["正式", "測試"], horizontal=True)
        else:
            env = "正式"
        chan = st.selectbox("通路", ["請選擇...", "MOMO", "寶雅", "康是美", "屈臣氏"])
        if st.button("鎖定環境並開始"):
            if chan != "請選擇...":
                st.session_state['current_channel'] = chan
                today = datetime.now().strftime("%Y%m%d")
                prefix = "TEST" if env == "測試" else "Back"
                conn = get_conn()
                cnt = conn.execute(f"SELECT COUNT(*) FROM return_batches WHERE batch_id LIKE '{prefix}{today}%'").fetchone()[0]
                batch_id = f"{prefix}{today}{cnt+1:03d}"
                conn.execute("INSERT INTO return_batches (batch_id, channel_name, create_date, status) VALUES (?, ?, ?, '作業中')", (batch_id, chan, today))
                st.session_state['current_batch_id'] = batch_id
                conn.commit(); conn.close(); st.rerun()
        
        if 'current_batch_id' in st.session_state and st.session_state['current_channel']:
            st.write(f"批號：{st.session_state['current_batch_id']}")
            bc = st.text_input("條碼")
            r_type = st.radio("箱/散", ["箱出", "散出"], horizontal=True)
            exp = st.text_input("效期")
            qty = st.number_input("數量", value=1)
            qual = st.radio("貨況", ["良品", "不良品"], horizontal=True)
            reason = st.text_input("異常原因")
            if st.button("儲存"):
                conn = get_conn()
                seq = conn.execute("SELECT COUNT(*) FROM return_items WHERE batch_id = ?", (st.session_state['current_batch_id'],)).fetchone()[0] + 1
                conn.execute('INSERT INTO return_items (batch_id, item_seq, barcode, return_type, expiry_date, quantity, quality_status, damage_reason, operator) VALUES (?,?,?,?,?,?,?,?,?)', 
                             (st.session_state['current_batch_id'], seq, bc, r_type, exp, qty, qual, reason, st.session_state['username']))
                conn.commit(); conn.close(); st.rerun()

    with tabs[1]:
        # 歷史查詢與資料呈現 (使用明確的欄位映射，防止衝突)
        conn = get_conn()
        query = """SELECT b.create_date AS '建檔日期', b.channel_name AS '通路', b.status AS '狀態', b.approved_by AS '簽核人', 
                          i.batch_id AS '批號', i.barcode AS '條碼', i.return_type AS '箱散出', i.expiry_date AS '效期', 
                          i.quantity AS '數量', i.quality_status AS '貨況', i.damage_reason AS '異常', i.operator AS '人員'
                   FROM return_items i LEFT JOIN return_batches b ON i.batch_id = b.batch_id"""
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("尚無歷史紀錄")

    with tabs[2]:
        if st.session_state['is_admin']:
            conn = get_conn()
            pending = pd.read_sql_query("SELECT * FROM return_batches WHERE status = '作業中'", conn)
            st.dataframe(pending, use_container_width=True)
            b_id = st.text_input("輸入要簽核的批號")
            if st.button("執行簽核"):
                conn.execute("UPDATE return_batches SET status = '已簽核', approved_by = ? WHERE batch_id = ?", (st.session_state['username'], b_id))
                conn.commit(); conn.close(); st.rerun()
        else:
            st.error("管理區僅限管理者訪問")
