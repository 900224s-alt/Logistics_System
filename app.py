import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(layout="wide")

# --- 1. 嚴謹的資料庫初始化 ---
def init_db():
    conn = sqlite3.connect('return_system.db')
    c = conn.cursor()
    # 建立用戶表
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, role TEXT)')
    # 建立退貨明細表 (確保欄位最完整)
    c.execute('''CREATE TABLE IF NOT EXISTS return_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    barcode TEXT, return_type TEXT, quantity INTEGER, 
                    quality_status TEXT, damage_reason TEXT, 
                    operator TEXT, approved TEXT DEFAULT '待簽核', 
                    create_date TEXT
                )''')
    # 強制初始化您的管理員權限
    try: c.execute("INSERT INTO users VALUES ('余宸緯', '管理者')")
    except: pass
    conn.commit(); conn.close()
init_db()

# --- 2. 登入系統 ---
if 'logged_in' not in st.session_state: 
    st.session_state.update({'logged_in': False, 'username': "", 'is_admin': False})

if not st.session_state['logged_in']:
    name = st.text_input("姓名")
    if st.button("登入"):
        if name == "余宸緯":
            st.session_state.update({'logged_in': True, 'username': name, 'is_admin': True})
            st.rerun()
        else:
            conn = sqlite3.connect('return_system.db')
            user = conn.execute('SELECT * FROM users WHERE username = ?', (name,)).fetchone()
            if user:
                st.session_state.update({'logged_in': True, 'username': name, 'is_admin': (user[1] == '管理者')})
                st.rerun()
            conn.close()
else:
    st.sidebar.write(f"👤 {st.session_state['username']}")
    if st.sidebar.button("登出"): st.session_state.update({'logged_in': False}); st.rerun()

    # --- 3. 所有分頁 ---
    tabs = st.tabs(["📦 點收作業", "🔍 歷史紀錄", "✅ 不良品簽核", "👥 人員管理"])
    
    # [點收]
    with tabs[0]:
        bc = st.text_input("條碼")
        rt = st.radio("箱/散", ["箱出", "散出"], horizontal=True)
        qty = st.number_input("數量", value=1)
        reason = st.text_input("異常原因")
        if st.button("儲存資料"):
            conn = sqlite3.connect('return_system.db')
            conn.execute('INSERT INTO return_items (barcode, return_type, quantity, quality_status, damage_reason, operator, create_date) VALUES (?,?,?,?,?,?,?)', 
                         (bc, rt, qty, "不良品" if "不良" in bc else "良品", reason, st.session_state['username'], datetime.now().strftime("%Y-%m-%d")))
            conn.commit(); conn.close(); st.success("儲存成功")

    # [歷史]
    with tabs[1]:
        conn = sqlite3.connect('return_system.db')
        df = pd.read_sql("SELECT * FROM return_items", conn)
        conn.close()
        st.dataframe(df, use_container_width=True, hide_index=True)

    # [簽核]
    with tabs[2]:
        if st.session_state['is_admin']:
            conn = sqlite3.connect('return_system.db')
            df = pd.read_sql("SELECT * FROM return_items WHERE quality_status='不良品' AND approved='待簽核'", conn)
            conn.close()
            df['簽核'] = False
            edited = st.data_editor(df, hide_index=True, column_config={"簽核": st.column_config.CheckboxColumn()})
            if st.button("執行選取簽核"):
                conn = sqlite3.connect('return_system.db')
                for i, row in edited.iterrows():
                    if row['簽核']: conn.execute("UPDATE return_items SET approved='已簽核' WHERE id=?", (int(row['id']),))
                conn.commit(); conn.close(); st.rerun()
        else: st.error("僅限管理員")

    # [人員]
    with tabs[3]:
        if st.session_state['is_admin']:
            conn = sqlite3.connect('return_system.db')
            users = pd.read_sql("SELECT * FROM users", conn)
            conn.close()
            st.dataframe(users, hide_index=True)
            t = st.text_input("員工姓名")
            if st.button("設為管理者"):
                conn = sqlite3.connect('return_system.db')
                conn.execute("UPDATE users SET role='管理者' WHERE username=?", (t,))
                conn.commit(); conn.close(); st.rerun()
        else: st.error("僅限管理員")
