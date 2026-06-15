import streamlit as st
import pandas as pd
import os
import sqlite3

st.set_page_config(layout="wide")

# 強制使用正確的資料儲存位置，避免路徑錯誤
DB_FILE = "return_system.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # 建立所有您需要的欄位
    c.execute('''CREATE TABLE IF NOT EXISTS return_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    barcode TEXT, 
                    quality_status TEXT, 
                    damage_reason TEXT, 
                    operator TEXT, 
                    approved TEXT DEFAULT '待簽核'
                )''')
    conn.commit(); conn.close()

init_db()

# 登入邏輯：這一次我保留了完整的登入判定
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'username': "", 'is_admin': False})

if not st.session_state['logged_in']:
    st.subheader("請登入系統")
    name = st.text_input("輸入姓名")
    if st.button("登入"):
        if name == "余宸緯":
            st.session_state.update({'logged_in': True, 'username': name, 'is_admin': True})
            st.rerun()
        else:
            st.error("目前僅開放管理者帳號登入進行測試。")
else:
    st.sidebar.write(f"目前使用者: {st.session_state['username']}")
    tabs = st.tabs(["📦 點收", "🔍 歷史", "✅ 簽核", "👥 管理"])

    # 1. 點收
    with tabs[0]:
        bc = st.text_input("輸入條碼")
        if st.button("確認存入"):
            conn = sqlite3.connect(DB_FILE)
            conn.execute('INSERT INTO return_items (barcode, quality_status, operator) VALUES (?,?,?)', 
                         (bc, "不良品", st.session_state['username']))
            conn.commit(); conn.close()
            st.success("資料已寫入")

    # 2. 歷史
    with tabs[1]:
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql("SELECT * FROM return_items", conn)
        conn.close()
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("目前資料庫為空，請先在「點收」分頁存入資料。")

    # 3. 簽核
    with tabs[2]:
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql("SELECT * FROM return_items WHERE quality_status='不良品' AND approved='待簽核'", conn)
        conn.close()
        if not df.empty:
            df['簽核'] = False
            edited = st.data_editor(df, hide_index=True, column_config={"簽核": st.column_config.CheckboxColumn()})
            if st.button("執行簽核"):
                conn = sqlite3.connect(DB_FILE)
                for i, row in edited.iterrows():
                    if row['簽核']:
                        conn.execute("UPDATE return_items SET approved='已簽核' WHERE id=?", (int(row['id']),))
                conn.commit(); conn.close(); st.rerun()
        else:
            st.info("暫無待簽核項目。")
