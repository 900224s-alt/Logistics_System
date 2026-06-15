import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="物流退貨點收系統", layout="wide")

# --- 1. 基礎架構 ---
def init_db():
    conn = sqlite3.connect('return_system.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS return_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        barcode TEXT, return_type TEXT, quantity INTEGER, 
                        quality_status TEXT, damage_reason TEXT, 
                        operator TEXT, approved TEXT DEFAULT '待簽核'
                    )''')
    conn.commit(); conn.close()
init_db()

# --- 2. 登入與權限判定 ---
if 'logged_in' not in st.session_state: 
    st.session_state.update({'logged_in': False, 'username': "", 'is_admin': False})

st.title("📦 物流退貨點收系統")

if not st.session_state['logged_in']:
    name = st.text_input("姓名")
    pwd = st.text_input("密碼", type="password")
    if st.button("登入"):
        # 【強制管理員識別邏輯】：只要名字對，直接給予管理者權限
        if name == "余宸緯":
            st.session_state.update({'logged_in': True, 'username': name, 'is_admin': True})
            st.rerun()
        else:
            conn = sqlite3.connect('return_system.db')
            user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (name, pwd)).fetchone()
            if user:
                st.session_state.update({'logged_in': True, 'username': name, 'is_admin': (user[2] == '管理者')})
                st.rerun()
            conn.close()
else:
    st.sidebar.write(f"👤 您好, {st.session_state['username']}")
    st.sidebar.write(f"🎖️ 身分: {'[👑 管理者]' if st.session_state['is_admin'] else '[一般用戶]'}")
    
    # 權限控管：強制渲染 Tabs
    if st.session_state['is_admin']:
        tabs = st.tabs(["📦 點收", "🔍 歷史", "✅ 不良品簽核", "👥 人員管理"])
    else:
        tabs = st.tabs(["📦 點收", "🔍 歷史"])

    with tabs[0]: # 點收
        bc = st.text_input("條碼")
        rtype = st.radio("類型", ["箱出", "散出"], horizontal=True)
        qty = st.number_input("數量", value=1)
        reason = st.text_input("異常原因")
        if st.button("儲存"):
            conn = sqlite3.connect('return_system.db')
            conn.execute('INSERT INTO return_items (barcode, return_type, quantity, quality_status, damage_reason, operator) VALUES (?,?,?,?,?,?)', 
                         (bc, rtype, qty, "不良品" if "不良" in bc else "良品", reason, st.session_state['username']))
            conn.commit(); conn.close(); st.success("儲存成功")

    with tabs[1]: # 歷史
        conn = sqlite3.connect('return_system.db')
        df = pd.read_sql("SELECT * FROM return_items", conn)
        conn.close()
        st.dataframe(df, use_container_width=True, hide_index=True)

    if st.session_state['is_admin']:
        with tabs[2]: # 簽核
            conn = sqlite3.connect('return_system.db')
            df = pd.read_sql("SELECT id, barcode, quality_status, damage_reason, operator FROM return_items WHERE quality_status='不良品' AND approved='待簽核'", conn)
            conn.close()
            df['簽核'] = False
            edited = st.data_editor(df, hide_index=True, column_config={"簽核": st.column_config.CheckboxColumn()})
            if st.button("確認簽核"):
                conn = sqlite3.connect('return_system.db')
                for i, row in edited.iterrows():
                    if row['簽核']: conn.execute("UPDATE return_items SET approved='已簽核' WHERE id=?", (row['id'],))
                conn.commit(); conn.close(); st.rerun()

        with tabs[3]: # 人員管理
            conn = sqlite3.connect('return_system.db')
            users = pd.read_sql("SELECT * FROM users", conn)
            conn.close()
            st.dataframe(users, hide_index=True)
            t = st.text_input("員工姓名")
            if st.button("設為管理者"):
                conn = sqlite3.connect('return_system.db')
                conn.execute("UPDATE users SET role='管理者' WHERE username=?", (t,))
                conn.commit(); conn.close(); st.rerun()
