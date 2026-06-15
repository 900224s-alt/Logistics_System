# 檔案名稱：app.py
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components
import io

# 設定頁面與版型
st.set_page_config(page_title="物流退貨點收系統", layout="wide")

# 💡 最高管理者設定
ORIGINAL_ADMIN = "余宸緯"

# ==========================================
# 💡 資料庫初始化 (完整版)
# ==========================================
def init_db_if_not_exists():
    conn = sqlite3.connect('return_system.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, register_date TEXT, role TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS return_batches (batch_id TEXT PRIMARY KEY, channel_name TEXT, create_date TEXT, status TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS return_items (id INTEGER PRIMARY KEY AUTOINCREMENT, batch_id TEXT, item_seq INTEGER, barcode TEXT, return_type TEXT, expiry_date TEXT, quantity INTEGER, quality_status TEXT, damage_reason TEXT, operator TEXT)''')
    conn.commit()
    conn.close()

init_db_if_not_exists()

def get_db_connection():
    conn = sqlite3.connect('return_system.db')
    conn.row_factory = sqlite3.Row
    return conn

# 初始化 Session 狀態
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'username' not in st.session_state: st.session_state['username'] = ""
if 'is_admin' not in st.session_state: st.session_state['is_admin'] = False
if 'current_channel' not in st.session_state: st.session_state['current_channel'] = ""
if 'current_batch_id' not in st.session_state: st.session_state['current_batch_id'] = ""
if 'btn_processing' not in st.session_state: st.session_state['btn_processing'] = False

st.title("📦 物流退貨點收系統")

# ==========================================
# 登入與註冊頁面
# ==========================================
if not st.session_state['logged_in']:
    tab1, tab2 = st.tabs(["👤 帳號登入", "📝 新人員註冊"])
    with tab1:
        login_name = st.text_input("請輸入中文真實姓名", key="login_name").strip()
        login_pwd = st.text_input("請輸入密碼", type="password", key="login_pwd")
        if st.button("進入系統"):
            conn = get_db_connection()
            user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (login_name, login_pwd)).fetchone()
            conn.close()
            if user:
                st.session_state.update({'logged_in': True, 'username': login_name, 'is_admin': (user['role'] == "管理者" or login_name == ORIGINAL_ADMIN)})
                st.rerun()
            else: st.error("❌ 姓名或密碼錯誤。")
    with tab2:
        reg_name = st.text_input("請輸入你的中文真實姓名", key="reg_name").strip()
        reg_pwd = st.text_input("自訂密碼", type="password", key="reg_pwd")
        if st.button("建立帳號"):
            if reg_name and reg_pwd:
                conn = get_db_connection()
                try:
                    conn.execute('INSERT INTO users (username, password, register_date, role) VALUES (?, ?, ?, ?)', 
                                 (reg_name, reg_pwd, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "一般用戶"))
                    conn.commit()
                    st.success("註冊成功！")
                except: st.error("❌ 已註冊或發生錯誤。")
                finally: conn.close()
else:
    # 登出與身份顯示
    st.sidebar.write(f"👤：**{st.session_state['username']}**")
    if st.sidebar.button("登出系統"): st.session_state['logged_in'] = False; st.rerun()

    tabs = st.tabs(["📦 退貨點收作業", "🔍 歷史紀錄與修改"])
    
    # --- 分頁一：點收作業 ---
    with tabs[0]:
        if st.session_state['current_channel'] == "":
            selected_chan = st.selectbox("🏬 選擇退貨通路", ["請選擇...", "MOMO", "寶雅", "康是美", "屈臣氏"])
            if st.button("鎖定並開始作業"):
                if selected_chan != "請選擇...":
                    st.session_state['current_channel'] = selected_chan
                    today = datetime.now().strftime("%Y%m%d")
                    conn = get_db_connection()
                    count = conn.execute("SELECT COUNT(*) FROM return_batches WHERE batch_id LIKE ?", (f"Back{today}%",)).fetchone()[0]
                    st.session_state['current_batch_id'] = f"Back{today}{count + 1:03d}"
                    conn.execute("INSERT INTO return_batches (batch_id, channel_name, create_date, status) VALUES (?, ?, ?, ?)", 
                                 (st.session_state['current_batch_id'], selected_chan, datetime.now().strftime("%Y-%m-%d"), "作業中"))
                    conn.commit(); conn.close(); st.rerun()
        else:
            st.info(f"批號：{st.session_state['current_batch_id']} | 通路：{st.session_state['current_channel']}")
            # 條碼輸入區
            barcode_val = st.text_input("請刷取或輸入條碼")
            ret_type = st.radio("類型", ["箱出", "散出"], horizontal=True)
            qty = st.number_input("數量", value=1)
            
            # 💡 防重複點擊機制
            if st.button("💾 儲存並繼續", type="primary", disabled=st.session_state['btn_processing']):
                if not barcode_val: st.error("請輸入條碼")
                else:
                    st.session_state['btn_processing'] = True
                    conn = get_db_connection()
                    seq = conn.execute("SELECT COUNT(*) FROM return_items WHERE batch_id = ?", (st.session_state['current_batch_id'],)).fetchone()[0] + 1
                    conn.execute('INSERT INTO return_items (batch_id, item_seq, barcode, return_type, quantity, operator) VALUES (?, ?, ?, ?, ?, ?)', 
                                 (st.session_state['current_batch_id'], seq, barcode_val, ret_type, qty, st.session_state['username']))
                    conn.commit(); conn.close()
                    st.session_state['btn_processing'] = False
                    st.success("成功儲存！")
                    st.rerun()

    # --- 分頁二：歷史紀錄 (包含篩選與匯出) ---
    with tabs[1]:
        st.header("🔍 歷史紀錄查詢")
        conn = get_db_connection()
        # 強制將 barcode 讀取為字串(str)以防止科學記號
        df = pd.read_sql_query("SELECT b.create_date, i.* FROM return_items i JOIN return_batches b ON i.batch_id = b.batch_id", conn, dtype={'barcode': str})
        conn.close()

        # 篩選區
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1: search_date = st.text_input("搜尋日期(YYYY-MM-DD)")
        with col_f2: search_bar = st.text_input("搜尋條碼")
        with col_f3: search_op = st.text_input("搜尋操作員")

        if not df.empty:
            # 欄位處理：將日期轉換格式並移除無用id
            df = df.drop(columns=['id'])
            
            # 執行篩選
            if search_date: df = df[df['create_date'].str.contains(search_date)]
            if search_bar: df = df[df['barcode'].str.contains(search_bar)]
            if search_op: df = df[df['operator'].str.contains(search_op)]

            st.dataframe(df, use_container_width=True)

            # Excel 匯出 (解決 csv 轉檔格式問題)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='點收報表')
            
            st.download_button(
                label="📥 下載 Excel 報表",
                data=output.getvalue(),
                file_name="Report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else: st.info("無資料")
