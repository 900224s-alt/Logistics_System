import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(layout="wide")

# 強制重新定義與補齊資料庫欄位
def init_db():
    conn = sqlite3.connect('return_system.db')
    c = conn.cursor()
    # 確保 users 表
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, role TEXT)')
    # 確保 return_items 表有所有必要的欄位
    c.execute('''CREATE TABLE IF NOT EXISTS return_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    barcode TEXT, quality_status TEXT, damage_reason TEXT, 
                    operator TEXT, approved TEXT DEFAULT '待簽核'
                )''')
    # 嘗試寫入管理員
    try: c.execute("INSERT INTO users VALUES ('余宸緯', '管理者')")
    except: pass
    conn.commit(); conn.close()

init_db()

# 簡單的登入判定
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'username': "", 'is_admin': False})

if not st.session_state['logged_in']:
    name = st.text_input("姓名")
    if st.button("登入"):
        if name == "余宸緯":
            st.session_state.update({'logged_in': True, 'username': name, 'is_admin': True})
            st.rerun()
else:
    st.sidebar.write(f"👤 {st.session_state['username']}")
    tabs = st.tabs(["📦 點收", "🔍 歷史", "✅ 不良品簽核", "👥 人員管理"])

    with tabs[0]: # 點收
        bc = st.text_input("條碼")
        if st.button("儲存"):
            conn = sqlite3.connect('return_system.db')
            conn.execute('INSERT INTO return_items (barcode, quality_status, operator) VALUES (?,?,?)', 
                         (bc, "不良品" if "不良" in bc else "良品", st.session_state['username']))
            conn.commit(); conn.close(); st.rerun()

    with tabs[1]: # 歷史紀錄 (不做任何 SQL 篩選)
        conn = sqlite3.connect('return_system.db')
        df = pd.read_sql("SELECT * FROM return_items", conn)
        conn.close()
        st.dataframe(df, use_container_width=True, hide_index=True)

    with tabs[2]: # 簽核
        if st.session_state['is_admin']:
            conn = sqlite3.connect('return_system.db')
            df = pd.read_sql("SELECT * FROM return_items", conn)
            conn.close()
            # 在 Python 端篩選，避免 SQL 語法錯誤
            if 'quality_status' in df.columns:
                df_bad = df[(df['quality_status'] == '不良品') & (df['approved'] == '待簽核')].copy()
                df_bad['簽核'] = False
                edited = st.data_editor(df_bad, hide_index=True, column_config={"簽核": st.column_config.CheckboxColumn()})
                if st.button("執行簽核"):
                    conn = sqlite3.connect('return_system.db')
                    for i, row in edited.iterrows():
                        if row['簽核']: conn.execute("UPDATE return_items SET approved='已簽核' WHERE id=?", (int(row['id']),))
                    conn.commit(); conn.close(); st.rerun()
            else: st.warning("資料欄位異常，請重啟系統")

    with tabs[3]: # 人員
        if st.session_state['is_admin']:
            conn = sqlite3.connect('return_system.db')
            users = pd.read_sql("SELECT * FROM users", conn)
            conn.close()
            st.dataframe(users, hide_index=True)
