import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="物流退貨點收系統", layout="wide")

ORIGINAL_ADMIN = "余宸緯"

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

# 登入狀態與環境初始化
if 'logged_in' not in st.session_state: 
    st.session_state.update({'logged_in': False, 'username': "", 'is_admin': False, 'current_channel': "", 'current_batch_id': ""})

st.title("📦 物流退貨點收系統")

if not st.session_state['logged_in']:
    tab1, tab2 = st.tabs(["👤 帳號登入", "📝 新人員註冊"])
    with tab1:
        name = st.text_input("姓名", key="l_n")
        pwd = st.text_input("密碼", type="password", key="l_p")
        if st.button("登入"):
            conn = get_conn()
            user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (name, pwd)).fetchone()
            if user:
                st.session_state.update({'logged_in': True, 'username': name, 'is_admin': (user['role'] == "管理者" or name == ORIGINAL_ADMIN)})
                conn.close(); st.rerun()
            conn.close()
    with tab2:
        r_name = st.text_input("真實姓名", key="r_n")
        r_pwd = st.text_input("密碼", type="password", key="r_p")
        if st.button("註冊"):
            conn = get_conn()
            try:
                conn.execute('INSERT INTO users VALUES (?, ?, ?, ?)', (r_name, r_pwd, datetime.now().strftime("%Y-%m-%d"), "一般用戶"))
                conn.commit(); st.success("註冊成功")
            except: st.error("帳號已存在")
            conn.close()
else:
    # 側邊欄顯示身份
    st.sidebar.write(f"👤 {st.session_state['username']}")
    st.sidebar.write(f"🎖️ 權限：{'管理者' if st.session_state['is_admin'] else '一般用戶'}")
    if st.sidebar.button("登出系統"): st.session_state.update({'logged_in': False}); st.rerun()
    
    tabs = st.tabs(["📦 退貨點收作業", "🔍 歷史紀錄與修改申請", "🔔 主管修改批核" if st.session_state['is_admin'] else ""])
    
    with tabs[0]:
        if st.session_state['is_admin']:
            env = st.radio("作業環境", ["正式環境", "測試環境"], horizontal=True)
        chan = st.selectbox("選擇退貨通路", ["請選擇...", "MOMO", "寶雅", "康是美", "屈臣氏"])
        if st.button("鎖定並開始作業"):
            st.session_state['current_channel'] = chan
            st.session_state['current_batch_id'] = f"Batch{datetime.now().strftime('%Y%m%d%H%M%S')}"
            conn = get_conn()
            conn.execute("INSERT INTO return_batches VALUES (?, ?, ?, '作業中', '')", (st.session_state['current_batch_id'], chan, datetime.now().strftime("%Y-%m-%d")))
            conn.commit(); conn.close(); st.rerun()
        
        if st.session_state['current_channel']:
            st.write(f"正在作業：{st.session_state['current_channel']} | 批號：{st.session_state['current_batch_id']}")
            # ... (點收輸入邏輯)
            if st.button("完成點收"): st.session_state['current_channel'] = ""; st.rerun()

    with tabs[1]:
        st.header("🔍 歷史紀錄")
        # 篩選區
        c1, c2, c3 = st.columns(3)
        start_d = c1.date_input("日期", value=datetime.now().date())
        filter_b = c2.text_input("條碼")
        filter_o = c3.text_input("作業員")
        
        conn = get_conn()
        df = pd.read_sql_query("SELECT b.create_date AS '建檔日期', i.batch_id AS '批號', i.barcode AS '條碼', i.return_type AS '類型', i.quantity AS '數量', i.operator AS '人員', b.status AS '狀態', b.approved_by AS '簽核人' FROM return_items i LEFT JOIN return_batches b ON i.batch_id = b.batch_id", conn)
        conn.close()
        
        if not df.empty:
            df['日期對比'] = pd.to_datetime(df['建檔日期'], errors='coerce').dt.date
            df = df[df['日期對比'] == start_d]
            st.dataframe(df.drop(columns=['日期對比']), use_container_width=True, hide_index=True)
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下載 CSV 報表", data=csv, file_name="report.csv", mime="text/csv")
        else: st.info("無紀錄")

    if st.session_state['is_admin']:
        with tabs[2]:
            st.header("🔔 主管修改批核")
            conn = get_conn()
            pending = pd.read_sql_query("SELECT * FROM return_batches WHERE status='作業中'", conn)
            st.dataframe(pending, use_container_width=True)
            bid = st.text_input("輸入批號簽核")
            if st.button("同意簽核"):
                conn.execute("UPDATE return_batches SET status='已簽核', approved_by=? WHERE batch_id=?", (st.session_state['username'], bid))
                conn.commit(); conn.close(); st.rerun()
