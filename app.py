import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="物流退貨點收系統", layout="wide")

# 💡 核心設定
ORIGINAL_ADMIN = "余宸緯"

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

# 狀態管理
if 'logged_in' not in st.session_state: 
    st.session_state.update({'logged_in': False, 'username': "", 'is_admin': False, 'current_channel': "", 'current_batch_id': ""})

st.title("📦 物流退貨點收系統")

if not st.session_state['logged_in']:
    tab1, tab2 = st.tabs(["👤 帳號登入", "📝 新人員註冊"])
    with tab1:
        name = st.text_input("姓名", key="n1")
        pwd = st.text_input("密碼", type="password", key="p1")
        if st.button("登入"):
            conn = get_conn()
            user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (name, pwd)).fetchone()
            if user:
                is_admin = (user['role'] == "管理者" or name == ORIGINAL_ADMIN)
                st.session_state.update({'logged_in': True, 'username': name, 'is_admin': is_admin})
                conn.close(); st.rerun()
            conn.close()
    with tab2:
        r_name = st.text_input("姓名", key="n2")
        r_pwd = st.text_input("密碼", type="password", key="p2")
        if st.button("註冊"):
            conn = get_conn()
            try:
                role = "管理者" if r_name == ORIGINAL_ADMIN else "一般用戶"
                conn.execute('INSERT INTO users VALUES (?, ?, ?, ?)', (r_name, r_pwd, datetime.now().strftime("%Y-%m-%d"), role))
                conn.commit(); st.success("註冊成功")
            except: st.error("帳號已存在")
            conn.close()
else:
    st.sidebar.write(f"👤 {st.session_state['username']} {'(👑 管理者)' if st.session_state['is_admin'] else ''}")
    if st.sidebar.button("登出"): st.session_state.update({'logged_in': False}); st.rerun()
    
    tabs_names = ["📦 退貨點收", "🔍 歷史紀錄"]
    if st.session_state['is_admin']: tabs_names.append("🔔 管理區")
    tabs = st.tabs(tabs_names)
    
    with tabs[0]:
        if st.session_state['current_channel'] == "":
            chan = st.selectbox("選擇通路", ["請選擇...", "MOMO", "寶雅", "康是美", "屈臣氏"])
            if st.button("鎖定並開始") and chan != "請選擇...":
                st.session_state['current_channel'] = chan
                today = datetime.now().strftime("%Y%m%d")
                conn = get_conn()
                cnt = conn.execute("SELECT COUNT(*) FROM return_batches WHERE batch_id LIKE ?", (f"Back{today}%",)).fetchone()[0]
                st.session_state['current_batch_id'] = f"Back{today}{cnt+1:03d}"
                conn.execute("INSERT INTO return_batches VALUES (?, ?, ?, '作業中')", (st.session_state['current_batch_id'], chan, today))
                conn.commit(); conn.close(); st.rerun()
        else:
            st.write(f"目前批號：{st.session_state['current_batch_id']}")
            bc = st.text_input("輸入條碼")
            if st.button("儲存"):
                conn = get_conn()
                seq = conn.execute("SELECT COUNT(*) FROM return_items WHERE batch_id = ?", (st.session_state['current_batch_id'],)).fetchone()[0] + 1
                conn.execute('INSERT INTO return_items (batch_id, item_seq, barcode, operator) VALUES (?, ?, ?, ?)', (st.session_state['current_batch_id'], seq, bc, st.session_state['username']))
                conn.commit(); conn.close(); st.rerun()
            if st.button("結束作業"): st.session_state['current_channel'] = ""; st.rerun()

    with tabs[1]:
        st.header("🔍 歷史紀錄")
        c1, c2, c3 = st.columns(3)
        start_d = c1.date_input("日期", value=None)
        filter_b = c2.text_input("條碼搜尋")
        filter_o = c3.text_input("作業員搜尋")
        
        conn = get_conn()
        query = """SELECT b.create_date, i.batch_id, i.item_seq, i.barcode, i.return_type, i.expiry_date, i.quantity, i.quality_status, i.damage_reason, i.operator 
                   FROM return_items i LEFT JOIN return_batches b ON i.batch_id = b.batch_id"""
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if not df.empty:
            df.rename(columns={'create_date': '建檔日期'}, inplace=True)
            df['建檔日期'] = df['建檔日期'].astype(str).str[:8]
            df['barcode'] = df['barcode'].astype(str).apply(lambda x: f"'{x}")
            
            if filter_b: df = df[df['barcode'].str.contains(filter_b)]
            if filter_o: df = df[df['operator'].str.contains(filter_o)]
            
            cols = ['建檔日期'] + [c for c in df.columns if c != '建檔日期']
            df = df[cols]
            
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下載 CSV 報表", data=csv, file_name="report.csv", mime="text/csv")
        else:
            st.info("暫無紀錄。")
    
    if st.session_state['is_admin']:
        with tabs[2]:
            st.header("🔔 管理區")
            st.write("管理者權限驗證成功，具備維護與批核功能。")
