import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from io import BytesIO

st.set_page_config(page_title="物流退貨點收系統", layout="wide")

ORIGINAL_ADMIN = "余宸緯"

# ==========================================
# 資料庫初始化與升級
# ==========================================
def init_db():
    conn = sqlite3.connect('return_system.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, register_date TEXT, role TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS return_batches (batch_id TEXT PRIMARY KEY, channel_name TEXT, create_date TEXT, status TEXT)')
    cursor.execute('''CREATE TABLE IF NOT EXISTS return_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, create_date TEXT, batch_id TEXT, item_seq INTEGER, 
                        barcode TEXT, return_type TEXT, expiry_date TEXT, quantity INTEGER, 
                        quality_status TEXT, damage_reason TEXT, operator TEXT)''')
    conn.commit(); conn.close()

init_db()

def get_db_connection():
    conn = sqlite3.connect('return_system.db')
    conn.row_factory = sqlite3.Row
    return conn

# ==========================================
# Session 初始化
# ==========================================
defaults = {"logged_in": False, "username": "", "is_admin": False, "current_channel": "", "current_batch_id": "", "saving": False}
for k, v in defaults.items():
    if k not in st.session_state: st.session_state[k] = v

# ==========================================
# 功能邏輯區
# ==========================================
def export_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="退貨紀錄")
        ws = writer.sheets["退貨紀錄"]
        # 設定條碼欄位為文字格式，防止科學記號
        for col_idx, col_name in enumerate(df.columns, 1):
            if col_name == "barcode":
                for cell in ws.iter_cols(min_row=2, min_col=col_idx, max_col=col_idx):
                    for c in cell: c.number_format = "@"
    return output.getvalue()

# ==========================================
# 頁面主體
# ==========================================
if not st.session_state["logged_in"]:
    tab1, tab2 = st.tabs(["👤 帳號登入", "📝 新人員註冊"])
    with tab1:
        u = st.text_input("姓名", key="in_u")
        p = st.text_input("密碼", type="password", key="in_p")
        if st.button("登入"):
            conn = get_db_connection()
            user = conn.execute('SELECT * FROM users WHERE username=? AND password=?', (u, p)).fetchone()
            conn.close()
            if user:
                st.session_state.update({"logged_in": True, "username": u, "is_admin": (u == ORIGINAL_ADMIN or user['role'] == '管理者')})
                st.rerun()
            else: st.error("帳號密碼錯誤")
    with tab2:
        u = st.text_input("姓名", key="reg_u")
        p = st.text_input("密碼", type="password", key="reg_p")
        if st.button("註冊"):
            conn = get_db_connection()
            try:
                conn.execute('INSERT INTO users VALUES (?,?,?,?)', (u, p, datetime.now().strftime("%Y-%m-%d"), "一般用戶"))
                conn.commit(); st.success("註冊成功")
            except: st.error("帳號已存在")
            finally: conn.close()
else:
    st.sidebar.write(f"使用者: **{st.session_state['username']}**")
    if st.sidebar.button("登出"): st.session_state.update(defaults); st.rerun()
    
    tabs = st.tabs(["📦 退貨點收作業", "🔍 歷史紀錄與報表"])
    
    with tabs[0]:
        if not st.session_state["current_channel"]:
            st.session_state["current_channel"] = st.selectbox("選擇通路", ["MOMO", "寶雅", "康是美", "屈臣氏"])
            if st.button("開始作業"): 
                st.session_state["current_batch_id"] = f"B{datetime.now().strftime('%Y%m%d%H%M')}"
                st.rerun()
        else:
            st.write(f"目前通路: {st.session_state['current_channel']} | 批號: {st.session_state['current_batch_id']}")
            barcode = st.text_input("商品條碼")
            if st.button("💾 儲存並繼續", disabled=st.session_state["saving"]):
                st.session_state["saving"] = True
                conn = get_db_connection()
                conn.execute("INSERT INTO return_items (create_date, batch_id, barcode, operator) VALUES (?,?,?,?)", 
                             (datetime.now().strftime("%Y/%m/%d"), st.session_state["current_batch_id"], str(barcode), st.session_state["username"]))
                conn.commit(); conn.close()
                st.session_state["saving"] = False
                st.toast("儲存成功"); st.rerun()

    with tabs[1]:
        conn = get_db_connection()
        c1, c2, c3 = st.columns(3)
        s_date = c1.text_input("日期(YYYY/MM/DD)")
        s_bar = c2.text_input("條碼")
        s_op = c3.text_input("人員")
        
        query = "SELECT * FROM return_items WHERE 1=1"
        params = []
        if s_date: query += " AND create_date = ?"; params.append(s_date)
        if s_bar: query += " AND barcode LIKE ?"; params.append(f"%{s_bar}%")
        if s_op: query += " AND operator LIKE ?"; params.append(f"%{s_op}%")
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        st.dataframe(df, use_container_width=True)
        if not df.empty:
            st.download_button("📥 下載 Excel 報表", data=export_excel(df), 
                               file_name=f"Report_{datetime.now().strftime('%Y%m%d')}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
