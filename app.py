import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import io
import streamlit.components.v1 as components

st.set_page_config(page_title="物流退貨點收系統", layout="wide")

# 💡 【最高管理者姓名設定】
ORIGINAL_ADMIN = "余宸緯" 

def init_db_if_not_exists():
    conn = sqlite3.connect('return_system.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT NOT NULL, register_date TEXT, role TEXT DEFAULT '一般用戶')''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS return_batches (batch_id TEXT PRIMARY KEY, channel_name TEXT, create_date TEXT, status TEXT DEFAULT '作業中')''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS return_items (id INTEGER PRIMARY KEY AUTOINCREMENT, batch_id TEXT, item_seq INTEGER, barcode TEXT, return_type TEXT, expiry_date TEXT, quantity INTEGER, quality_status TEXT, damage_reason TEXT, operator TEXT)''')
    conn.commit()
    conn.close()

init_db_if_not_exists()

def get_db_connection():
    conn = sqlite3.connect('return_system.db')
    conn.row_factory = sqlite3.Row
    return conn

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

# 初始化 Session
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'username' not in st.session_state: st.session_state['username'] = ""
if 'is_admin' not in st.session_state: st.session_state['is_admin'] = False
if 'current_channel' not in st.session_state: st.session_state['current_channel'] = ""
if 'current_batch_id' not in st.session_state: st.session_state['current_batch_id'] = ""

st.title("📦 物流退貨點收系統")

if not st.session_state['logged_in']:
    tab1, tab2 = st.tabs(["👤 帳號登入", "📝 新人員註冊"])
    with tab1:
        st.subheader("使用者登入")
        login_name = st.text_input("請輸入中文真實姓名", key="login_name").strip()
        login_pwd = st.text_input("請輸入密碼", type="password", key="login_pwd")
        if st.button("進入系統", use_container_width=True):
            if login_name and login_pwd:
                conn = get_db_connection()
                user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (login_name, login_pwd)).fetchone()
                conn.close()
                if user:
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = login_name
                    if user['role'] == "管理者" or login_name == ORIGINAL_ADMIN: st.session_state['is_admin'] = True
                    st.success(f"🎉 歡迎【{login_name}】上工。")
                    st.rerun()
                else: st.error("❌ 姓名或密碼錯誤。")
    with tab2:
        st.subheader("新人員註冊")
        reg_name = st.text_input("請輸入你的中文真實姓名", key="reg_name").strip()
        reg_pwd = st.text_input("自訂密碼", type="password", key="reg_pwd")
        if st.button("建立帳號", use_container_width=True):
            if reg_name and reg_pwd:
                conn = get_db_connection()
                try:
                    initial_role = "管理者" if reg_name == ORIGINAL_ADMIN else "一般用戶"
                    conn.execute('INSERT INTO users (username, password, register_date, role) VALUES (?, ?, ?, ?)', (reg_name, reg_pwd, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), initial_role))
                    conn.commit()
                    st.success(f"👍 【{reg_name}】註冊成功！請切換到[帳號登入]。")
                except sqlite3.IntegrityError: st.error("❌ 這個姓名已被註冊。")
                finally: conn.close()
else:
    st.sidebar.write(f"👤 作業員：**{st.session_state['username']}**")
    if st.sidebar.button("登出系統"): st.session_state['logged_in'] = False; st.rerun()

    tabs_list = ["📦 退貨點收作業", "🔍 歷史紀錄與修改申請"]
    if st.session_state['is_admin']: tabs_list.extend(["🔔 主管修改批核", "👥 員工權限與離職維護"])
    tabs = st.tabs(tabs_list)
    
    with tabs[0]:
        if st.session_state['current_channel'] == "":
            selected_chan = st.selectbox("🏬 選擇退貨通路", ["請選擇...", "MOMO", "寶雅", "康是美", "屈臣氏"])
            if st.button("鎖定並開始作業", use_container_width=True):
                if selected_chan != "請選擇...":
                    st.session_state['current_channel'] = selected_chan
                    today_str = datetime.now().strftime("%Y%m%d")
                    conn = get_db_connection()
                    count = conn.execute("SELECT COUNT(*) FROM return_batches WHERE batch_id LIKE ?", (f"Back{today_str}%",)).fetchone()[0]
                    conn.close()
                    st.session_state['current_batch_id'] = f"Back{today_str}{count + 1:03d}"
                    st.rerun()
        else:
            st.info(f"🏬 通路：**{st.session_state['current_channel']}** ｜ 🧾 批號：**{st.session_state['current_batch_id']}**")
            final_barcode = st.text_input("最終確認條碼")
            if st.button("儲存"):
                conn = get_db_connection()
                seq = conn.execute("SELECT COUNT(*) FROM return_items WHERE batch_id = ?", (st.session_state['current_batch_id'],)).fetchone()[0] + 1
                conn.execute('INSERT INTO return_items (batch_id, item_seq, barcode, operator) VALUES (?, ?, ?, ?)', (st.session_state['current_batch_id'], seq, final_barcode, st.session_state['username']))
                conn.commit(); conn.close(); st.rerun()
            if st.button("完成"): st.session_state['current_channel'] = ""; st.rerun()

    with tabs[1]:
        st.header("🔍 歷史紀錄與篩選")
        with st.expander("📊 篩選查詢條件", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1: start_date = st.date_input("起始日期", value=None)
            with col2: filter_barcode = st.text_input("篩選條碼")
            with col3: filter_op = st.text_input("篩選作業員")

        conn = get_db_connection()
        # 修正：只選取需要的欄位，避免重複鍵錯誤
        df = pd.read_sql_query("SELECT b.create_date AS raw_date, i.* FROM return_items i LEFT JOIN return_batches b ON i.batch_id = b.batch_id", conn)
        conn.close()

        if not df.empty:
            # 修正：先處理日期字串，避免無法轉換
            df['建檔日期'] = df['raw_date'].fillna('').astype(str).str[:8]
            df['建檔日期'] = df['建檔日期'].apply(lambda x: f"{x[:4]}/{x[4:6]}/{x[6:]}" if len(x)==8 else x)
            df['barcode'] = df['barcode'].astype(str).apply(lambda x: f"'{x}")
            
            if filter_barcode: df = df[df['barcode'].str.contains(filter_barcode)]
            if filter_op: df = df[df['operator'].str.contains(filter_op)]
            
            # 移除隱藏欄位，只展示給使用者看的
            display_df = df.drop(columns=['raw_date', 'create_date', 'id'], errors='ignore')
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            st.download_button("📥 下載 XLSX 報表", data=to_excel(display_df), file_name="report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else: st.info("尚無歷史單據。")
