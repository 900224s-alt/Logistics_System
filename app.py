import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="物流退貨點收系統", layout="wide")

# 資料庫初始化 (絕對不能動的基礎)
def init_db():
    conn = sqlite3.connect('return_system.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, register_date TEXT, role TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS return_batches (batch_id TEXT PRIMARY KEY, channel_name TEXT, create_date TEXT, status TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS return_items (id INTEGER PRIMARY KEY AUTOINCREMENT, batch_id TEXT, item_seq INTEGER, barcode TEXT, return_type TEXT, expiry_date TEXT, quantity INTEGER, quality_status TEXT, damage_reason TEXT, operator TEXT)''')
    conn.commit(); conn.close()

init_db()

def get_conn():
    conn = sqlite3.connect('return_system.db')
    conn.row_factory = sqlite3.Row
    return conn

# 狀態初始化
if 'logged_in' not in st.session_state: 
    st.session_state.update({'logged_in': False, 'username': "", 'is_admin': False, 'current_channel': "", 'current_batch_id': ""})

st.title("📦 物流退貨點收系統")

if not st.session_state['logged_in']:
    # [登入註冊邏輯維持不變]
    name = st.text_input("姓名", key="n1")
    pwd = st.text_input("密碼", type="password", key="p1")
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
    
    tabs = st.tabs(["📦 作業環境與點收", "🔍 歷史紀錄"])
    
    # 分頁 1：作業環境 (邏輯與歷史完全分離)
    with tabs[0]:
        env = st.radio("環境選擇", ["正式環境", "測試環境"], horizontal=True, key="env_sel")
        chan = st.selectbox("通路選擇", ["請選擇...", "MOMO", "寶雅", "康是美", "屈臣氏"], key="chan_sel")
        if st.button("鎖定環境並開始"):
            if chan != "請選擇...":
                st.session_state['current_channel'] = chan
                today = datetime.now().strftime("%Y%m%d")
                prefix = "TEST" if env == "測試環境" else "Back"
                conn = get_conn()
                cnt = conn.execute(f"SELECT COUNT(*) FROM return_batches WHERE batch_id LIKE '{prefix}{today}%'").fetchone()[0]
                st.session_state['current_batch_id'] = f"{prefix}{today}{cnt+1:03d}"
                conn.execute("INSERT INTO return_batches VALUES (?, ?, ?, '作業中')", (st.session_state['current_batch_id'], chan, today))
                conn.commit(); conn.close(); st.rerun()
        
        if st.session_state['current_channel']:
            st.write(f"目前批號：{st.session_state['current_batch_id']}")
            bc = st.text_input("條碼")
            if st.button("儲存"):
                conn = get_conn()
                conn.execute('INSERT INTO return_items (batch_id, barcode, operator) VALUES (?, ?, ?)', (st.session_state['current_batch_id'], bc, st.session_state['username']))
                conn.commit(); conn.close(); st.rerun()

    # 分頁 2：歷史紀錄 (完全獨立的資料查詢邏輯)
    with tabs[1]:
        c1, c2 = st.columns(2)
        start_d = c1.date_input("查詢日期", value=datetime.now().date())
        filter_b = c2.text_input("搜尋條碼")
        
        conn = get_conn()
        # 查詢語句與點收邏輯完全脫鉤，確保讀取安全性
        df = pd.read_sql_query("SELECT b.create_date, i.batch_id, i.barcode, i.operator FROM return_items i LEFT JOIN return_batches b ON i.batch_id = b.batch_id", conn)
        conn.close()
        
        if not df.empty:
            df.rename(columns={'create_date': '建檔日期'}, inplace=True)
            df['日期欄位'] = pd.to_datetime(df['建檔日期'], errors='coerce').dt.date
            
            # 使用 .copy() 避免設定警告，篩選條件獨立
            display_df = df[df['日期欄位'] == start_d].copy()
            if filter_b: display_df = display_df[display_df['barcode'].astype(str).str.contains(filter_b)]
            
            st.dataframe(display_df.drop(columns=['日期欄位']), use_container_width=True, hide_index=True)
        else:
            st.info("該日期無資料，請確認是否已完成儲存。")
