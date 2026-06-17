import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="物流退貨點收系統", layout="centered")

ORIGINAL_ADMIN = "余宸緯" 

def get_db_connection():
    conn = sqlite3.connect('return_system.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(return_items)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'created_at' not in columns:
        conn.execute("ALTER TABLE return_items ADD COLUMN created_at TEXT")
        conn.commit()
    conn.close()

init_db()

# 確保審核狀態欄位存在
conn = get_db_connection()
try:
    conn.execute("ALTER TABLE return_items ADD COLUMN approval_status TEXT DEFAULT '已確認'")
    conn.commit()
except: pass
conn.close()

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'username' not in st.session_state: st.session_state['username'] = ""
if 'is_admin' not in st.session_state: st.session_state['is_admin'] = False
if 'current_channel' not in st.session_state: st.session_state['current_channel'] = ""
if 'current_batch_id' not in st.session_state: st.session_state['current_batch_id'] = ""
if 'current_env' not in st.session_state: st.session_state['current_env'] = "正式環境"
if 'is_batch_saved' not in st.session_state: st.session_state['is_batch_saved'] = False

st.title("📦 物流退貨點收系統")

if not st.session_state['logged_in']:
    tab1, tab2 = st.tabs(["👤 帳號登入", "📝 新人員註冊"])
    with tab1:
        st.subheader("使用者登入")
        login_name = st.text_input("請輸入中文真實姓名", key="login_name").strip()
        login_pwd = st.text_input("請輸入密碼", type="password", key="login_pwd")
        if st.button("進入系統", use_container_width=True):
            conn = get_db_connection()
            user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (login_name, login_pwd)).fetchone()
            conn.close()
            if user:
                st.session_state.update({'logged_in': True, 'username': login_name, 'is_admin': (user['role'] == "管理者" or login_name == ORIGINAL_ADMIN)})
                st.rerun()
            else: st.error("❌ 姓名或密碼錯誤。")
    with tab2:
        st.subheader("新人員註冊")
        reg_name = st.text_input("請輸入你的中文真實姓名", key="reg_name").strip()
        reg_pwd = st.text_input("自訂密碼", type="password", key="reg_pwd")
        if st.button("建立帳號", use_container_width=True):
            conn = get_db_connection()
            try:
                conn.execute('INSERT INTO users (username, password, register_date, role) VALUES (?, ?, ?, ?)', (reg_name, reg_pwd, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "一般用戶"))
                conn.commit(); st.success("註冊成功！")
            finally: conn.close()
else:
    if st.sidebar.button("登出系統"): st.session_state.clear(); st.rerun()
    tabs = st.tabs(["📦 退貨點收作業", "🔍 歷史紀錄與修改申請", "🔔 主管修改批核", "👥 員工權限與離職維護"])
    
    with tabs[0]:
        if st.session_state['current_channel'] == "":
            env_choice = st.radio("⚙️ 請選擇作業環境", ["正式環境", "測試環境"], horizontal=True) if st.session_state['is_admin'] else "正式環境"
            selected_chan = st.selectbox("🏬 選擇退貨通路", ["請選擇...", "MOMO", "寶雅", "康是美", "屈臣氏", "蝦皮", "家購", "大智通", "好事多"])
            if st.button("鎖定並開始作業"):
                if selected_chan != "請選擇...":
                    st.session_state['current_channel'] = selected_chan
                    st.session_state['current_env'] = env_choice
                    today_str = datetime.now().strftime("%Y%m%d")
                    prefix = "TEST" if env_choice == "測試環境" else "Back"
                    conn = get_db_connection()
                    count = conn.execute("SELECT COUNT(*) FROM return_batches WHERE batch_id LIKE ?", (f"{prefix}{today_str}%",)).fetchone()[0]
                    conn.close()
                    st.session_state['current_batch_id'] = f"{prefix}{today_str}{count + 1:03d}"
                    st.rerun()
        else:
            st.info(f"🏬 {st.session_state['current_channel']} ｜ 🧾 {st.session_state['current_batch_id']}")
            barcode_input = st.text_input("🔍 刷取條碼")
            ret_type = st.radio("形態", ["箱出", "散出"], horizontal=True)
            if barcode_input and st.button("💾 儲存並繼續"):
                conn = get_db_connection()
                conn.execute('''INSERT INTO return_items (batch_id, barcode, return_type, operator, approval_status, created_at) VALUES (?, ?, ?, ?, '已確認', ?)''', 
                            (st.session_state['current_batch_id'], barcode_input, ret_type, st.session_state['username'], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit(); conn.close(); st.success("✅ 儲存成功！"); st.rerun()

    with tabs[1]:
        st.header("🔍 歷史紀錄與更正")
        with st.expander("⚙️ 篩選條件", expanded=True):
            col1, col2 = st.columns(2)
            s_start = col1.date_input("開始日期", value=None)
            s_end = col2.date_input("結束日期", value=None)
            s_batch = st.text_input("批號")
            s_barcode = st.text_input("條碼")
            s_type = st.multiselect("形態", ["箱出", "散出"])
            s_quality = st.multiselect("貨況", ["良品", "不良品"])
            if st.button("查詢數據"):
                conn = get_db_connection()
                query = "SELECT * FROM return_items WHERE 1=1"
                params = []
                if s_start: query += " AND created_at >= ?"; params.append(str(s_start))
                if s_batch: query += " AND batch_id LIKE ?"; params.append(f"%{s_batch}%")
                if s_barcode: query += " AND barcode LIKE ?"; params.append(f"%{s_barcode}%")
                if s_type: query += f" AND return_type IN ({','.join(['?']*len(s_type))})"; params.extend(s_type)
                if s_quality: query += f" AND quality_status IN ({','.join(['?']*len(s_quality))})"; params.extend(s_quality)
                st.session_state['df'] = pd.read_sql_query(query, conn, params=params); conn.close()

        if 'df' in st.session_state:
            st.dataframe(st.session_state['df'], use_container_width=True)
            target_id = st.number_input("輸入要異動的 ID", min_value=1, step=1)
            action = st.selectbox("動作", ["修改數量", "轉換貨況", "申請刪除資料"])
            if st.button("提交申請 (送至主管審核)"):
                conn = get_db_connection()
                new_status = '審核中'
                if action == "申請刪除資料":
                    conn.execute("UPDATE return_items SET approval_status = '申請刪除' WHERE id = ?", (target_id,))
                else:
                    conn.execute("UPDATE return_items SET approval_status = '審核中' WHERE id = ?", (target_id,))
                conn.commit(); conn.close(); st.success("申請已送出！"); st.rerun()

    with tabs[2]:
        st.header("🔔 主管審核工作台")
        conn = get_db_connection()
        review_df = pd.read_sql_query("SELECT * FROM return_items WHERE approval_status IN ('審核中', '申請刪除')", conn)
        conn.close()
        st.dataframe(review_df, use_container_width=True)
        app_id = st.number_input("處理單據 ID", min_value=1, step=1)
        if st.button("✅ 核准 (若為刪除申請則執行刪除)"):
            conn = get_db_connection()
            row = conn.execute("SELECT approval_status FROM return_items WHERE id = ?", (app_id,)).fetchone()
            if row and row['approval_status'] == '申請刪除':
                conn.execute("DELETE FROM return_items WHERE id = ?", (app_id,))
            else:
                conn.execute("UPDATE return_items SET approval_status = '已確認' WHERE id = ?", (app_id,))
            conn.commit(); conn.close(); st.success("執行完畢"); st.rerun()
