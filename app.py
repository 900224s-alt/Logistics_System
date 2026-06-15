import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="物流退貨點收系統", layout="wide")

# 1. 基礎資料庫初始化
def init_db():
    conn = sqlite3.connect('return_system.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, register_date TEXT, role TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS return_batches (batch_id TEXT PRIMARY KEY, channel_name TEXT, create_date TEXT, status TEXT, approved_by TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS return_items (id INTEGER PRIMARY KEY AUTOINCREMENT, batch_id TEXT, barcode TEXT, return_type TEXT, expiry_date TEXT, quantity INTEGER, quality_status TEXT, damage_reason TEXT, operator TEXT, approved TEXT DEFAULT '待簽核')''')
    conn.commit(); conn.close()
init_db()

def get_conn():
    conn = sqlite3.connect('return_system.db')
    return conn

# 2. Session 初始化
if 'logged_in' not in st.session_state: 
    st.session_state.update({'logged_in': False, 'username': "", 'is_admin': False})

st.title("📦 物流退貨點收系統")

# 登入區
if not st.session_state['logged_in']:
    name = st.text_input("姓名")
    pwd = st.text_input("密碼", type="password")
    if st.button("登入"):
        conn = get_conn()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (name, pwd)).fetchone()
        if user:
            st.session_state.update({'logged_in': True, 'username': name, 'is_admin': (user[3] == "管理者")})
            conn.close(); st.rerun()
        conn.close()
else:
    # 側邊欄：顯示登入者身分
    st.sidebar.write(f"👤 {st.session_state['username']}")
    if st.sidebar.button("登出"): st.session_state.update({'logged_in': False}); st.rerun()
    
    tabs = st.tabs(["📦 點收", "🔍 歷史", "✅ 不良品簽核", "👥 人員管理"])
    
    # --- A. 點收 ---
    with tabs[0]:
        chan = st.selectbox("通路", ["MOMO", "寶雅", "康是美", "屈臣氏"])
        bc = st.text_input("條碼")
        rtype = st.radio("箱/散", ["箱出", "散出"], horizontal=True)
        qty = st.number_input("數量", value=1)
        if st.button("儲存"):
            conn = get_conn()
            conn.execute('INSERT INTO return_items (batch_id, barcode, return_type, quantity, quality_status, operator) VALUES (?,?,?,?,?,?)', 
                         ("BATCH001", bc, rtype, qty, "不良品" if "不良" in bc else "良品", st.session_state['username']))
            conn.commit(); conn.close(); st.success("儲存成功")

    # --- B. 歷史 ---
    with tabs[1]:
        conn = get_conn()
        # 簡單查詢，不使用任何複雜別名
        df = pd.read_sql("SELECT * FROM return_items", conn)
        conn.close()
        # 隱藏索引欄位
        st.dataframe(df, use_container_width=True, hide_index=True)
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載 CSV", csv, "report.csv")

    # --- C. 簽核 ---
    with tabs[2]:
        if st.session_state['is_admin']:
            conn = get_conn()
            # 簡單查詢
            df_bad = pd.read_sql("SELECT * FROM return_items WHERE quality_status='不良品' AND approved='待簽核'", conn)
            conn.close()
            
            # 使用編輯器提供勾選
            if not df_bad.empty:
                df_bad['簽核'] = False
                edited = st.data_editor(df_bad, hide_index=True)
                if st.button("確認簽核"):
                    conn = get_conn()
                    for idx, row in edited.iterrows():
                        if row['簽核']:
                            conn.execute("UPDATE return_items SET approved='已簽核' WHERE id=?", (row['id'],))
                    conn.commit(); conn.close(); st.rerun()
            else: st.info("無待簽核不良品")
        else: st.error("僅限管理者")

    # --- D. 人員管理 ---
    with tabs[3]:
        if st.session_state['is_admin']:
            conn = get_conn()
            users = pd.read_sql("SELECT username, role FROM users", conn)
            st.dataframe(users, hide_index=True)
            t = st.text_input("姓名")
            if st.button("升為管理員"):
                conn.execute("UPDATE users SET role='管理者' WHERE username=?", (t,))
                conn.commit(); conn.close(); st.rerun()
        else: st.error("僅限管理者")
