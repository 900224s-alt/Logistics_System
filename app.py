import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="物流退貨點收系統", layout="wide")

# 核心設定
ORIGINAL_ADMIN = "余宸緯"

def init_db():
    conn = sqlite3.connect('return_system.db')
    cursor = conn.cursor()
    # 用戶表
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, register_date TEXT, role TEXT)''')
    # 批次表：增加簽核人欄位
    cursor.execute('''CREATE TABLE IF NOT EXISTS return_batches (batch_id TEXT PRIMARY KEY, channel_name TEXT, create_date TEXT, status TEXT, approved_by TEXT)''')
    # 點收明細表：補齊所有欄位
    cursor.execute('''CREATE TABLE IF NOT EXISTS return_items (id INTEGER PRIMARY KEY AUTOINCREMENT, batch_id TEXT, barcode TEXT, return_type TEXT, expiry_date TEXT, quantity INTEGER, quality_status TEXT, damage_reason TEXT, operator TEXT)''')
    conn.commit(); conn.close()

init_db()

def get_conn():
    conn = sqlite3.connect('return_system.db')
    conn.row_factory = sqlite3.Row
    return conn

# Session 管理
if 'logged_in' not in st.session_state: 
    st.session_state.update({'logged_in': False, 'username': "", 'is_admin': False})

st.title("📦 物流退貨點收系統")

if not st.session_state['logged_in']:
    tab1, tab2 = st.tabs(["👤 帳號登入", "📝 新人員註冊"])
    with tab1:
        name = st.text_input("姓名", key="l1")
        pwd = st.text_input("密碼", type="password", key="p1")
        if st.button("登入"):
            conn = get_conn()
            user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (name, pwd)).fetchone()
            if user:
                st.session_state.update({'logged_in': True, 'username': name, 'is_admin': (user['role'] == "管理者" or name == ORIGINAL_ADMIN)})
                conn.close(); st.rerun()
            conn.close()
    with tab2:
        r_name = st.text_input("姓名", key="l2")
        r_pwd = st.text_input("密碼", type="password", key="p2")
        if st.button("註冊"):
            conn = get_conn()
            try:
                conn.execute('INSERT INTO users VALUES (?, ?, ?, ?)', (r_name, r_pwd, datetime.now().strftime("%Y-%m-%d"), "一般用戶"))
                conn.commit(); st.success("註冊成功")
            except: st.error("帳號已存在")
            conn.close()
else:
    st.sidebar.write(f"👤 {st.session_state['username']} {'(👑 管理者)' if st.session_state['is_admin'] else ''}")
    if st.sidebar.button("登出"): st.session_state.update({'logged_in': False}); st.rerun()
    
    tabs = st.tabs(["📦 點收作業", "🔍 歷史紀錄", "✅ 不良品簽核", "👥 人員管理"])
    
    # 1. 點收作業
    with tabs[0]:
        if st.session_state['is_admin']: env = st.radio("環境", ["正式環境", "測試環境"], horizontal=True)
        else: env = "正式環境"
        chan = st.selectbox("通路", ["MOMO", "寶雅", "康是美", "屈臣氏"])
        if st.button("鎖定環境"):
            st.session_state['bid'] = f"{'TEST' if env == '測試環境' else 'Back'}{datetime.now().strftime('%Y%m%d%H%M%S')}"
            conn = get_conn()
            conn.execute("INSERT INTO return_batches VALUES (?, ?, ?, '作業中', '')", (st.session_state['bid'], chan, datetime.now().strftime("%Y-%m-%d")))
            conn.commit(); conn.close(); st.rerun()
        
        if 'bid' in st.session_state:
            st.write(f"當前批號：{st.session_state['bid']}")
            bc = st.text_input("條碼")
            rtype = st.radio("箱/散", ["箱出", "散出"], horizontal=True)
            exp = st.text_input("效期")
            qty = st.number_input("數量", value=1)
            qual = st.radio("貨況", ["良品", "不良品"], horizontal=True)
            reas = st.text_input("異常原因")
            if st.button("儲存資料"):
                conn = get_conn()
                conn.execute('INSERT INTO return_items (batch_id, barcode, return_type, expiry_date, quantity, quality_status, damage_reason, operator) VALUES (?,?,?,?,?,?,?,?)',
                             (st.session_state['bid'], bc, rtype, exp, qty, qual, reas, st.session_state['username']))
                conn.commit(); conn.close(); st.rerun()

    # 2. 歷史紀錄
    with tabs[1]:
        conn = get_conn()
        query = "SELECT b.create_date AS '日期', i.* FROM return_items i LEFT JOIN return_batches b ON i.batch_id = b.batch_id"
        df = pd.read_sql(query, conn)
        conn.close()
        # 篩選器
        d_filter = st.date_input("日期篩選")
        st.dataframe(df, use_container_width=True, hide_index=True)
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載CSV", csv, "report.csv")

    # 3. 不良品簽核
    with tabs[2]:
        if st.session_state['is_admin']:
            conn = get_conn()
            df_bad = pd.read_sql("SELECT * FROM return_items WHERE quality_status='不良品'", conn)
            st.dataframe(df_bad)
            bid_sign = st.text_input("輸入要簽核的批號")
            if st.button("批次核准"):
                conn.execute("UPDATE return_batches SET status='已簽核', approved_by=? WHERE batch_id=?", (st.session_state['username'], bid_sign))
                conn.commit(); conn.close(); st.rerun()
        else: st.error("無權限")

    # 4. 人員管理
    with tabs[3]:
        if st.session_state['is_admin']:
            conn = get_conn()
            users = pd.read_sql("SELECT * FROM users", conn)
            st.dataframe(users)
            target = st.text_input("要設定的員工姓名")
            if st.button("升為管理者"):
                conn.execute("UPDATE users SET role='管理者' WHERE username=?", (target,))
                conn.commit(); conn.close(); st.rerun()
        else: st.error("無權限")
