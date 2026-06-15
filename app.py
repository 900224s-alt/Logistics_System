import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(layout="wide")

# 強制使用絕對路徑建立資料庫，並使用原生 SQL 讀取，不依賴 pandas 的 SQL 解析器
def get_data(query):
    conn = sqlite3.connect('return_system.db')
    try:
        data = pd.read_sql_query(query, conn)
    except:
        # 如果 read_sql 報錯，改用最原始的游標讀取
        cursor = conn.execute(query)
        data = pd.DataFrame(cursor.fetchall(), columns=[d[0] for d in cursor.description])
    conn.close()
    return data

def init_db():
    conn = sqlite3.connect('return_system.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, role TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS return_items (id INTEGER PRIMARY KEY AUTOINCREMENT, barcode TEXT, quality_status TEXT, operator TEXT, approved TEXT DEFAULT "待簽核")')
    try: c.execute("INSERT INTO users VALUES ('余宸緯', '管理者')")
    except: pass
    conn.commit(); conn.close()
init_db()

# 登入判定
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'username': "", 'is_admin': False})

if not st.session_state['logged_in']:
    name = st.text_input("姓名")
    if st.button("登入"):
        if name == "余宸緯":
            st.session_state.update({'logged_in': True, 'username': name, 'is_admin': True})
            st.rerun()
else:
    st.sidebar.write(f"👤 {st.session_state['username']} {'(管理者)' if st.session_state['is_admin'] else ''}")
    tabs = st.tabs(["📦 點收", "🔍 歷史", "✅ 簽核", "👥 人員"])

    with tabs[0]: # 點收
        bc = st.text_input("條碼")
        if st.button("儲存"):
            conn = sqlite3.connect('return_system.db')
            conn.execute('INSERT INTO return_items (barcode, quality_status, operator) VALUES (?,?,?)', (bc, "不良品", st.session_state['username']))
            conn.commit(); conn.close(); st.rerun()

    with tabs[1]: # 歷史
        df = get_data("SELECT * FROM return_items")
        st.dataframe(df, use_container_width=True, hide_index=True)

    with tabs[2]: # 簽核
        if st.session_state['is_admin']:
            df = get_data("SELECT * FROM return_items WHERE quality_status='不良品' AND approved='待簽核'")
            df['簽核'] = False
            edited = st.data_editor(df, hide_index=True, column_config={"簽核": st.column_config.CheckboxColumn()})
            if st.button("確定簽核"):
                conn = sqlite3.connect('return_system.db')
                for i, row in edited.iterrows():
                    if row['簽核']: conn.execute("UPDATE return_items SET approved='已簽核' WHERE id=?", (int(row['id']),))
                conn.commit(); conn.close(); st.rerun()

    with tabs[3]: # 人員
        if st.session_state['is_admin']:
            users = get_data("SELECT * FROM users")
            st.dataframe(users, hide_index=True)
