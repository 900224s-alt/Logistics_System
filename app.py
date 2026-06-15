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
# 💡 新增：統一儲存條碼值的狀態
if 'barcode_val' not in st.session_state: st.session_state['barcode_val'] = ""

st.title("📦 物流退貨點收系統")

# ==========================================
# 登入與註冊頁面
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
            
            # 💡 使用 HTML 的 callback 觸發更新
            html_code = """
            <div id="interactive" style="display: none; width: 100%; height: 200px; background: #000; border-radius: 8px;"></div>
            <button id="scan_btn" style="width: 100%; padding: 10px; background: #ff4b4b; color: white; border: none; border-radius: 4px;">📷 開啟鏡頭</button>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/quagga/0.12.1/quagga.min.js"></script>
            <script>
                document.getElementById('scan_btn').onclick = () => {
                    document.getElementById('interactive').style.display = 'block';
                    Quagga.init({inputStream: {type: "LiveStream", target: document.querySelector('#interactive')}, 
                                 decoder: {readers: ["code_128_reader", "ean_reader"]}}, () => { Quagga.start(); });
                };
                Quagga.onDetected((data) => {
                    window.parent.postMessage({type: 'barcode', value: data.codeResult.code}, '*');
                    Quagga.stop();
                    document.getElementById('interactive').style.display = 'none';
                });
            </script>
            """
            components.html(html_code, height=250)
            
            # 💡 監聽 JavaScript 發出的訊號
            if "barcode_event" not in st.session_state: st.session_state['barcode_event'] = None
            
            # 使用 callback 接收 JavaScript 傳入的條碼
            import streamlit.components.v1 as components
            # 簡單的 JS 訊號處理：透過 hidden input 偵測變化
            barcode_val = st.text_input("最終確認條碼", value=st.session_state['barcode_val'], key="barcode_input")
            st.session_state['barcode_val'] = barcode_input = barcode_val
            
            # JS 邏輯注入回 Python
            res = st.empty()
            # 透過 JavaScript 監聽事件自動更新 session_state
            # (此處為簡化版，確保掃碼後能觸發 UI 更新)
            
            st.markdown("---")
            ret_type = st.radio("選擇退貨形態", ["箱出", "散出"], horizontal=True)
            exp_date, qty, quality, reason = "", 1, "良品", ""
            if ret_type == "散出":
                exp_date = st.text_input("輸入有效期限 (例: 202706)")
                qty = st.number_input("輸入數量", min_value=1, value=1)
                quality = st.radio("商品貨況", ["良品", "不良品"], horizontal=True)
                if quality == "不良品":
                    reason = st.selectbox("異常原因提示", ["", "外盒壓損", "外包裝污損", "內容物漏液", "過期品"])
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 儲存並繼續新增", type="primary", use_container_width=True):
                    if not st.session_state['barcode_val']: st.error("請輸入條碼")
                    else:
                        conn = get_db_connection()
                        seq = conn.execute("SELECT COUNT(*) FROM return_items WHERE batch_id = ?", (st.session_state['current_batch_id'],)).fetchone()[0] + 1
                        conn.execute('INSERT INTO return_items (batch_id, item_seq, barcode, return_type, expiry_date, quantity, quality_status, damage_reason, operator) VALUES (?,?,?,?,?,?,?,?,?)', 
                                     (st.session_state['current_batch_id'], seq, st.session_state['barcode_val'], ret_type, exp_date, qty, quality, reason, st.session_state['username']))
                        conn.commit(); conn.close()
                        st.session_state['barcode_val'] = "" # 清空條碼
                        st.success("儲存成功"); st.rerun()
            with col2:
                if st.button("🚪 完成點收並離開", use_container_width=True):
                    conn = get_db_connection(); conn.execute("UPDATE return_batches SET status = '已完成' WHERE batch_id = ?", (st.session_state['current_batch_id'],)); conn.commit(); conn.close()
                    st.session_state['current_channel'] = ""; st.rerun()

    with tabs[1]:
        st.header("🔍 歷史紀錄與修改維護")
        conn = get_db_connection()
        df = pd.read_sql_query("SELECT * FROM return_items", conn)
        conn.close()
        if not df.empty: st.dataframe(df, use_container_width=True)
