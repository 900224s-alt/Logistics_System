# 檔案名稱：app.py
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components

st.set_page_config(page_title="物流退貨點收系統", layout="centered")

# 💡 【最高管理者姓名設定】
ORIGINAL_ADMIN = "余宸緯" 

# ==========================================
# 💡 自動初始化資料庫
# ==========================================
def init_db_if_not_exists():
    conn = sqlite3.connect('return_system.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            register_date TEXT,
            role TEXT DEFAULT '一般用戶'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS return_batches (
            batch_id TEXT PRIMARY KEY,
            channel_name TEXT,
            create_date TEXT,
            status TEXT DEFAULT '作業中'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS return_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id TEXT,
            item_seq INTEGER,
            barcode TEXT,
            return_type TEXT,
            expiry_date TEXT,
            quantity INTEGER,
            quality_status TEXT,
            damage_reason TEXT,
            operator TEXT
        )
    ''')
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
if 'current_env' not in st.session_state: st.session_state['current_env'] = "正式環境"

st.title("📦 物流退貨點收系統")

# ==========================================
# 登入與註冊頁面 (維持原樣)
# ==========================================
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
                    if user['role'] == "管理者" or login_name == ORIGINAL_ADMIN:
                        st.session_state['is_admin'] = True
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

# ==========================================
# 系統主頁面
# ==========================================
else:
    st.sidebar.write(f"👤 作業員：**{st.session_state['username']}**")
    st.sidebar.write(f"🎖️ 權限：**{'管理者' if st.session_state['is_admin'] else '一般用戶'}**")
    if st.sidebar.button("登出系統"):
        st.session_state['logged_in'] = False; st.rerun()

    tabs_list = ["📦 退貨點收作業", "🔍 歷史紀錄與修改申請"]
    if st.session_state['is_admin']: 
        tabs_list.extend(["🔔 主管修改批核", "👥 員工權限與離職維護"])
        
    tabs = st.tabs(tabs_list)
    
    # --- 分頁一：退貨點收作業 ---
    with tabs[0]:
        if st.session_state['current_channel'] == "":
            st.subheader("🚀 請設定本次作業環境與通路")
            if st.session_state['is_admin']: env_choice = st.radio("⚙️ 作業環境", ["正式環境", "測試環境"], horizontal=True)
            else: env_choice = "正式環境"
            selected_chan = st.selectbox("🏬 選擇退貨通路", ["請選擇...", "MOMO", "寶雅", "康是美", "屈臣氏"])
            
            if st.button("鎖定並開始作業", use_container_width=True):
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
            st.info(f"🏬 通路：**{st.session_state['current_channel']}** ｜ 🧾 批號：**{st.session_state['current_batch_id']}**")
            
            st.markdown("### 📷 請掃描或輸入條碼")
            
            # 使用組件直接輸入，不再需要額外欄位
            barcode_bridge = components.html(
                """
                <input type="text" id="barcode_input" placeholder="請刷條碼或手動輸入..." style="width: 100%; padding: 15px; font-size: 18px; border: 2px solid #ff4b4b; border-radius: 5px;">
                <script>
                    const input = document.getElementById('barcode_input');
                    input.addEventListener('input', (e) => {
                        window.parent.postMessage({type: 'streamlit:setComponentValue', value: e.target.value}, '*');
                    });
                </script>
                """, height=70, key="direct_barcode_input"
            )

            st.markdown("---")
            ret_type = st.radio("選擇退貨形態", ["箱出", "散出"], horizontal=True)
            
            # 依據選擇顯示細項
            if ret_type == "散出":
                exp_date = st.text_input("輸入有效期限 (例: 202706)")
                qty = st.number_input("輸入數量", min_value=1, value=1)
                quality = st.radio("商品貨況", ["良品", "不良品"], horizontal=True)
                reason = st.selectbox("異常原因提示", ["", "外盒壓損", "外包裝污損", "內容物漏液", "過期品"]) if quality == "不良品" else ""
            else:
                qty, exp_date, quality, reason = 1, "", "良品", ""

            # 存檔邏輯：直接拿 direct_barcode_input 的值
            if st.button("💾 儲存並繼續新增", use_container_width=True, type="primary"):
                target_barcode = st.session_state.get('direct_barcode_input', '').strip()
                if not target_barcode:
                    st.error("❌ 尚未讀取到條碼值！")
                elif ret_type == "散出" and not exp_date:
                    st.error("❌ 散出必須填寫效期！")
                else:
                    conn = get_db_connection()
                    today_str = datetime.now().strftime("%Y%m%d")
                    conn.execute("INSERT OR IGNORE INTO return_batches VALUES (?, ?, ?, '作業中')", (st.session_state['current_batch_id'], st.session_state['current_channel'], today_str))
                    seq = conn.execute("SELECT COUNT(*) FROM return_items WHERE batch_id = ?", (st.session_state['current_batch_id'],)).fetchone()[0] + 1
                    conn.execute('''INSERT INTO return_items (batch_id, item_seq, barcode, return_type, expiry_date, quantity, quality_status, damage_reason, operator)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', (st.session_state['current_batch_id'], seq, target_barcode, ret_type, exp_date, qty, quality, reason, st.session_state['username']))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ 條碼 {target_barcode} 儲存成功！")
                    st.rerun()

    # --- 歷史紀錄分頁 ---
    with tabs[1]:
        st.header("🔍 歷史紀錄與修改維護")
        conn = get_db_connection()
        df = pd.read_sql_query("SELECT * FROM return_items", conn)
        conn.close()
        if not df.empty: st.dataframe(df, use_container_width=True)
        else: st.info("尚無歷史單據。")
