import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import io
import streamlit.components.v1 as components

st.set_page_config(page_title="物流退貨點收系統", layout="wide")

# 💡 管理者設定
ORIGINAL_ADMIN = "余宸緯" 

def init_db_if_not_exists():
    conn = sqlite3.connect('return_system.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT NOT NULL, register_date TEXT, role TEXT DEFAULT '一般用戶')''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS return_batches (batch_id TEXT PRIMARY KEY, channel_name TEXT, create_date TEXT, status TEXT DEFAULT '作業中')''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS return_items (id INTEGER PRIMARY KEY AUTOINCREMENT, batch_id TEXT, item_seq INTEGER, barcode TEXT, return_type TEXT, expiry_date TEXT, quantity INTEGER, quality_status TEXT, damage_reason TEXT, operator TEXT)''')
    conn.commit(); conn.close()

init_db_if_not_exists()

def get_db_connection():
    conn = sqlite3.connect('return_system.db')
    conn.row_factory = sqlite3.Row
    return conn

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

# 初始化 Session
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'username' not in st.session_state: st.session_state['username'] = ""
if 'is_admin' not in st.session_state: st.session_state['is_admin'] = False
if 'current_channel' not in st.session_state: st.session_state['current_channel'] = ""

st.title("📦 物流退貨點收系統")

if not st.session_state['logged_in']:
    tab1, tab2 = st.tabs(["👤 帳號登入", "📝 新人員註冊"])
    with tab1:
        login_name = st.text_input("請輸入姓名", key="ln").strip()
        login_pwd = st.text_input("密碼", type="password", key="lp")
        if st.button("進入系統"):
            conn = get_db_connection()
            user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (login_name, login_pwd)).fetchone()
            if user:
                st.session_state.update({'logged_in': True, 'username': login_name, 'is_admin': (user['role'] == "管理者" or login_name == ORIGINAL_ADMIN)})
                conn.close(); st.rerun()
            conn.close()
    with tab2:
        reg_name = st.text_input("真實姓名", key="rn")
        reg_pwd = st.text_input("密碼", type="password", key="rp")
        if st.button("註冊"):
            conn = get_db_connection()
            try:
                conn.execute('INSERT INTO users VALUES (?, ?, ?, ?)', (reg_name, reg_pwd, datetime.now().strftime("%Y-%m-%d"), "管理者" if reg_name == ORIGINAL_ADMIN else "一般用戶"))
                conn.commit(); st.success("註冊成功"); 
            except: st.error("帳號已存在")
            conn.close()
else:
    st.sidebar.write(f"👤 {st.session_state['username']} ({'管理者' if st.session_state['is_admin'] else '一般用戶'})")
    if st.sidebar.button("登出"): st.session_state['logged_in'] = False; st.rerun()

    tabs_list = ["📦 退貨點收", "🔍 歷史紀錄"]
    if st.session_state['is_admin']: tabs_list.extend(["🔔 管理批核", "👥 員工維護"])
    tabs = st.tabs(tabs_list)
    
    with tabs[1]:
        st.header("🔍 歷史紀錄")
        col1, col2, col3 = st.columns(3)
        start_date = col1.date_input("日期")
        filter_bc = col2.text_input("條碼")
        filter_op = col3.text_input("作業員")

        conn = get_db_connection()
        # 修正 SQL 避免欄位重複，明確指定欄位
        query = "SELECT b.create_date, i.batch_id, i.item_seq, i.barcode, i.return_type, i.expiry_date, i.quantity, i.quality_status, i.damage_reason, i.operator FROM return_items i LEFT JOIN return_batches b ON i.batch_id = b.batch_id"
        df = pd.read_sql_query(query, conn)
        conn.close()

        if not df.empty:
            df.rename(columns={'create_date': '建檔日期'}, inplace=True)
            df['建檔日期'] = pd.to_datetime(df['建檔日期']).dt.strftime('%Y/%m/%d')
            # 將建檔日期移至最前
            cols = ['建檔日期'] + [c for c in df.columns if c != '建檔日期']
            df = df[cols]
            
            df['barcode'] = df['barcode'].astype(str).apply(lambda x: f"'{x}")
            
            if filter_bc: df = df[df['barcode'].str.contains(filter_bc)]
            if filter_op: df = df[df['operator'].str.contains(filter_op)]
            
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.download_button("📥 下載 XLSX", data=to_excel(df), file_name="report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else: st.info("無資料")
