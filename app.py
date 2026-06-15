import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(layout="wide")

# 1. 初始化資料庫 (確保欄位最簡潔)
def init_db():
    conn = sqlite3.connect('return_system.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)''')
    # 確保這張表存在
    c.execute('''CREATE TABLE IF NOT EXISTS return_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    barcode TEXT, return_type TEXT, quantity INTEGER, 
                    quality_status TEXT, damage_reason TEXT, 
                    operator TEXT, approved TEXT DEFAULT '待簽核'
                )''')
    conn.commit(); conn.close()
init_db()

# 2. 登入邏輯
if 'logged_in' not in st.session_state: 
    st.session_state.update({'logged_in': False, 'username': "", 'is_admin': False})

if not st.session_state['logged_in']:
    name = st.text_input("姓名")
    pwd = st.text_input("密碼", type="password")
    if st.button("登入"):
        if name == "余宸緯": # 強制指定管理者
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
    st.sidebar.write(f"👤 {st.session_state['username']}")
    if st.sidebar.button("登出"): st.session_state.update({'logged_in': False}); st.rerun()
    
    # 強制顯示所有標籤頁
    tabs = st.tabs(["📦 點收", "🔍 歷史", "✅ 不良品簽核", "👥 人員管理"])
    
    with tabs[0]: # 點收
        bc = st.text_input("條碼")
        if st.button("儲存"):
            conn = sqlite3.connect('return_system.db')
            conn.execute('INSERT INTO return_items (barcode, quality_status, operator) VALUES (?,?,?)', 
                         (bc, "不良品" if "不良" in bc else "良品", st.session_state['username']))
            conn.commit(); conn.close(); st.success("儲存成功")

    with tabs[1]: # 歷史紀錄
        conn = sqlite3.connect('return_system.db')
        df = pd.read_sql("SELECT * FROM return_items", conn)
        conn.close()
        # hide_index=True 徹底移除那欄索引
        st.dataframe(df, use_container_width=True, hide_index=True)

    with tabs[2]: # 不良品簽核
        if st.session_state['is_admin']:
            conn = sqlite3.connect('return_system.db')
            df = pd.read_sql("SELECT * FROM return_items WHERE quality_status='不良品' AND approved='待簽核'", conn)
            conn.close()
            # 勾選式簽核
            edited = st.data_editor(df, hide_index=True, column_config={"approved": st.column_config.CheckboxColumn()})
            if st.button("確認勾選簽核"):
                conn = sqlite3.connect('return_system.db')
                for i, row in edited.iterrows():
                    if row['approved']: # 邏輯簡化
                        conn.execute("UPDATE return_items SET approved='已簽核' WHERE id=?", (row['id'],))
                conn.commit(); conn.close(); st.rerun()
        else: st.error("僅限管理員")

    with tabs[3]: # 人員管理
        if st.session_state['is_admin']:
            conn = sqlite3.connect('return_system.db')
            users = pd.read_sql("SELECT * FROM users", conn)
            st.dataframe(users, hide_index=True)
