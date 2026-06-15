import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# 設定頁面與版面
st.set_page_config(page_title="物流退貨點收系統", layout="wide")

# --- 1. 資料庫初始化 (最穩定架構) ---
def init_db():
    conn = sqlite3.connect('return_system.db')
    cursor = conn.cursor()
    # 建立用戶與退貨記錄表
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS return_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        barcode TEXT, return_type TEXT, quantity INTEGER, 
                        quality_status TEXT, damage_reason TEXT, 
                        operator TEXT, approved TEXT DEFAULT '待簽核', 
                        create_date TEXT
                    )''')
    conn.commit(); conn.close()

init_db()

# --- 2. 登入與管理員權限判定 ---
if 'logged_in' not in st.session_state: 
    st.session_state.update({'logged_in': False, 'username': "", 'is_admin': False})

st.title("📦 物流退貨點收系統")

# 登入頁面
if not st.session_state['logged_in']:
    name = st.text_input("姓名")
    pwd = st.text_input("密碼", type="password")
    if st.button("登入"):
        # 強制管理員判斷
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
    # 側邊欄顯示
    st.sidebar.write(f"👤 您好, {st.session_state['username']}")
    st.sidebar.write(f"🎖️ 權限: {'[👑 管理者]' if st.session_state['is_admin'] else '[一般用戶]'}")
    if st.sidebar.button("登出"): st.session_state.update({'logged_in': False}); st.rerun()
    
    # 全部功能的 Tabs (強制顯現)
    tabs = st.tabs(["📦 點收作業", "🔍 歷史紀錄", "✅ 不良品簽核", "👥 人員管理"])
    
    # A. 點收作業
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

    # B. 歷史紀錄 (直接讀取，無複雜 SQL)
    with tabs[1]:
        conn = sqlite3.connect('return_system.db')
        df = pd.read_sql("SELECT * FROM return_items", conn)
        conn.close()
        # 隱藏索引列，顯示全部資料
        st.dataframe(df, use_container_width=True, hide_index=True)
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載CSV", csv, "report.csv")

    # C. 不良品簽核 (勾選機制)
    with tabs[2]:
        if st.session_state['is_admin']:
            conn = sqlite3.connect('return_system.db')
            df = pd.read_sql("SELECT id, barcode, quality_status, damage_reason, operator, create_date FROM return_items WHERE quality_status='不良品' AND approved='待簽核'", conn)
            conn.close()
            # 建立勾選欄位
            df['簽核'] = False
            edited = st.data_editor(df, hide_index=True, column_config={"簽核": st.column_config.CheckboxColumn()})
            if st.button("執行選取簽核"):
                conn = sqlite3.connect('return_system.db')
                for i, row in edited.iterrows():
                    if row['簽核']: conn.execute("UPDATE return_items SET approved='已簽核' WHERE id=?", (row['id'],))
                conn.commit(); conn.close(); st.rerun()
        else: st.error("僅限管理者使用")

    # D. 人員管理
    with tabs[3]:
        if st.session_state['is_admin']:
            conn = sqlite3.connect('return_system.db')
            users = pd.read_sql("SELECT * FROM users", conn)
            st.dataframe(users, hide_index=True)
            t = st.text_input("輸入員工名稱")
            if st.button("設為管理者"):
                conn.execute("UPDATE users SET role='管理者' WHERE username=?", (t,))
                conn.commit(); conn.close(); st.rerun()
        else: st.error("僅限管理者使用")
