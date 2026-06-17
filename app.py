import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="物流退貨點收系統", layout="centered")

ORIGINAL_ADMIN = "余宸緯" 

# 定義 25 種異常原因清單
DAMAGE_REASONS = [
    "盒凹", "嚴重盒凹", "盒污", "畫痕", 
    "已過期（一個月內）", "即期（兩個月內）", "短效（半年內）", 
    "效期模糊", "批號模糊", "已開封", "已開封使用", 
    "空盒", "膠膜破損", "膠膜嚴重破損", "膠膜污損", 
    "色差", "漸層色差", "嚴重色差", "霧氣", 
    "漏液", "嚴重漏液", "外盒有貼標籤", "外膜有貼標籤", 
    "外膜有貼膠帶+盒內有貼標籤", "外盒有貼膠帶+盒內有貼標籤"
]

def get_db_connection():
    conn = sqlite3.connect('return_system.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, register_date TEXT, role TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS return_batches 
                      (batch_id TEXT PRIMARY KEY, channel TEXT, date TEXT, status TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS return_items 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, batch_id TEXT, barcode TEXT, return_type TEXT, 
                       expiry_date TEXT, quantity INTEGER, quality_status TEXT, damage_reason TEXT, 
                       operator TEXT, approval_status TEXT, created_at TEXT)''')
    
    cursor.execute("PRAGMA table_info(return_items)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'created_at' not in columns:
        conn.execute("ALTER TABLE return_items ADD COLUMN created_at TEXT")
        conn.commit()
    conn.close()

init_db()

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'username' not in st.session_state: st.session_state['username'] = ""
if 'is_admin' not in st.session_state: st.session_state['is_admin'] = False
if 'current_channel' not in st.session_state: st.session_state['current_channel'] = ""
if 'current_batch_id' not in st.session_state: st.session_state['current_batch_id'] = ""
if 'current_env' not in st.session_state: st.session_state['current_env'] = "正式環境"

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
                    st.session_state['is_admin'] = (user['role'] == "管理者" or login_name == ORIGINAL_ADMIN)
                    st.success(f"🎉 歡迎【{login_name}】上工。")
                    st.rerun()
                else: st.error("❌ 姓名或密碼錯誤。")
            else: st.warning("⚠️ 請輸入姓名與密碼。")
    with tab2:
        st.subheader("新人員註冊")
        reg_name = st.text_input("請輸入你的中文真實姓名", key="reg_name").strip()
        reg_pwd = st.text_input("自訂密碼", type="password", key="reg_pwd")
        if st.button("建立帳號", use_container_width=True):
            if reg_name and reg_pwd:
                conn = get_db_connection()
                try:
                    initial_role = "管理者" if reg_name == ORIGINAL_ADMIN else "一般用戶"
                    conn.execute('INSERT INTO users (username, password, register_date, role) VALUES (?, ?, ?, ?)', 
                                 (reg_name, reg_pwd, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), initial_role))
                    conn.commit()
                    st.success(f"👍 【{reg_name}】註冊成功！請切換到[帳號登入]。")
                except sqlite3.IntegrityError: st.error("❌ 這個姓名已被註冊。")
                finally: conn.close()
            else: st.warning("⚠️ 欄位不能留空。")
else:
    st.sidebar.write(f"👤 作業員：**{st.session_state['username']}**")
    st.sidebar.write(f"🎖️ 權限：**{'管理者' if st.session_state['is_admin'] else '一般用戶'}**")
    if st.sidebar.button("登出系統"):
        st.session_state.clear()
        st.rerun()

    tabs = st.tabs(["📦 退貨點收作業", "🔍 歷史紀錄與修改申請", "🔔 主管修改批核", "👥 員工權限與離職維護"])
    
    with tabs[0]:
        if st.session_state['current_channel'] == "":
            st.subheader("🚀 請領取單號並設定作業環境")
            env_choice = st.radio("⚙️ 請選擇作業環境", ["正式環境", "測試環境"], horizontal=True) if st.session_state['is_admin'] else "正式環境"
            selected_chan = st.selectbox("🏬 選擇退貨通路", ["請選擇...", "MOMO", "寶雅", "康是美", "屈臣氏", "蝦皮", "家購", "大智通", "好市多","PCHPME","松本清","唐吉訶德"])
            if st.button("🚀 領取單號並開始作業", use_container_width=True):
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
                else: st.warning("⚠️ 請選擇通路！")
        else:
            env_label = "⚠️【測試環境】" if st.session_state['current_env'] == "測試環境" else "🟢【正式環境】"
            st.markdown(f"### {env_label}")
            st.info(f"🏬 通路：**{st.session_state['current_channel']}** ｜ 🧾 領取批號：**{st.session_state['current_batch_id']}**")
            
            # --- 作業進度儀表板 ---
            conn = get_db_connection()
            data_now = conn.execute("SELECT COUNT(*), SUM(quantity) FROM return_items WHERE batch_id = ?", (st.session_state['current_batch_id'],)).fetchone()
            bad_now = conn.execute("SELECT COUNT(*) FROM return_items WHERE batch_id = ? AND quality_status = '不良品'", (st.session_state['current_batch_id'],)).fetchone()
            conn.close()
            c1, c2, c3 = st.columns(3)
            c1.metric("總點收筆數", data_now[0] or 0)
            c2.metric("總數量", data_now[1] or 0)
            c3.metric("不良品筆數", bad_now[0] or 0)
            
            c_nav1, c_nav2 = st.columns(2)
            if c_nav1.button("⬅️ 返回通路選擇 (暫停作業)"):
                st.session_state['current_channel'] = ""
                st.session_state['current_batch_id'] = ""
                st.rerun()
            if c_nav2.button("⏹️ 封單完成"):
                st.session_state['current_channel'] = ""
                st.session_state['current_batch_id'] = ""
                st.rerun()
            
            st.markdown("---")
            barcode_input = st.text_input("🔍 請刷取商品條碼或手動輸入", key="barcode_field")
            if barcode_input: st.success(f"📥 目前帶入條碼：**{barcode_input}**")
            
            ret_type = st.radio("選擇退貨形態", ["箱出", "散出"], horizontal=True)
            qty, exp_date, quality, reason = 1, "", "良品", ""
            if ret_type == "散出":
                exp_date = st.text_input("輸入有效期限 (例: 202706)")
                qty = st.number_input("輸入數量", min_value=1, value=1)
                quality = st.radio("商品貨況", ["良品", "不良品"], horizontal=True)
                if quality == "不良品":
                    reasons = st.multiselect("勾選不良品原因", DAMAGE_REASONS)
                    reason = ", ".join(reasons)
            
            if st.button("💾 儲存並繼續新增", use_container_width=True, type="primary"):
                conn = get_db_connection()
                conn.execute("INSERT OR IGNORE INTO return_batches VALUES (?, ?, ?, '作業中')", (st.session_state['current_batch_id'], st.session_state['current_channel'], datetime.now().strftime("%Y%m%d")))
                conn.execute('''INSERT INTO return_items (batch_id, barcode, return_type, expiry_date, quantity, quality_status, damage_reason, operator, approval_status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, '已確認', ?)''', 
                            (st.session_state['current_batch_id'], barcode_input, ret_type, exp_date, qty, quality, reason, st.session_state['username'], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit(); conn.close(); st.success("✅ 儲存成功！"); st.rerun()

    with tabs[1]:
        st.header("🔍 歷史紀錄與更正")
        if st.button("查詢數據"):
            conn = get_db_connection()
            st.dataframe(pd.read_sql_query("SELECT * FROM return_items", conn))
            conn.close()

    with tabs[2]:
        st.header("🔔 主管修改批核")
        if st.session_state['is_admin']:
            conn = get_db_connection()
            st.dataframe(pd.read_sql_query("SELECT * FROM return_items WHERE approval_status IN ('審核中', '申請刪除')", conn))
            conn.close()
        else: st.error("僅管理員可訪問")

    with tabs[3]:
        st.header("👥 員工權限與離職維護")
        if st.session_state['is_admin']:
            conn = get_db_connection()
            users_df = pd.read_sql_query("SELECT username AS 中文姓名, register_date AS 註冊日期, role AS 目前身分 FROM users", conn)
            st.dataframe(users_df, use_container_width=True)
            target_user = st.text_input("請輸入要操作的員工姓名").strip()
            c1, c2, c3 = st.columns(3)
            if c1.button("🎖️ 升職為管理者"):
                conn.execute("UPDATE users SET role = '管理者' WHERE username = ?", (target_user,)); conn.commit(); st.rerun()
            if c2.button("👤 降職為一般用戶"):
                conn.execute("UPDATE users SET role = '一般用戶' WHERE username = ?", (target_user,)); conn.commit(); st.rerun()
            if c3.button("❌ 刪除此用戶"):
                conn.execute("DELETE FROM users WHERE username = ?", (target_user,)); conn.commit(); st.rerun()
            conn.close()
        else: st.error("僅管理員可訪問")
