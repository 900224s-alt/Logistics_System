import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import io
import streamlit.components.v1 as components

st.set_page_config(page_title="物流退貨點收系統", layout="wide")

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

# 💡 瓶頸1：新增 XLSX 匯出功能
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

# 初始化 Session 狀態
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'username' not in st.session_state: st.session_state['username'] = ""
if 'is_admin' not in st.session_state: st.session_state['is_admin'] = False
if 'current_channel' not in st.session_state: st.session_state['current_channel'] = ""
if 'current_batch_id' not in st.session_state: st.session_state['current_batch_id'] = ""
if 'current_env' not in st.session_state: st.session_state['current_env'] = "正式環境"

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
            
            st.markdown("**📷 高精準鏡頭辨識區**")
            
            components.html(
                """
                <div id="scanner_container" style="position: relative; width: 100%; font-family: sans-serif;">
                    <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 10px;">
                        <input type="text" id="barcode_display" placeholder="手動、藍牙槍或等待鏡頭嗶聲" 
                               style="flex: 1; padding: 12px; font-size: 16px; border: 1px solid #ccc; border-radius: 4px;">
                        <button id="scan_btn" style="padding: 12px 20px; font-size: 16px; background-color: #ff4b4b; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold;">
                            📷 啟動相機
                        </button>
                    </div>
                    <div id="interactive" class="viewport" style="display: none; position: relative; width: 100%; height: 300px; border: 3px solid #ff4b4b; border-radius: 8px; overflow: hidden; background: #000;">
                        <div style="position: absolute; top: 35%; left: 10%; width: 80%; height: 30%; border: 2px dashed #ffeb3b; background: rgba(255, 235, 59, 0.1); border-radius: 4px; box-sizing: border-box; z-index: 99999; pointer-events: none;"></div>
                        <div style="position: absolute; top: 50% !important; left: 12% !important; width: 76% !important; height: 3px !important; background-color: #ff0000 !important; box-shadow: 0 0 10px #ff0000 !important; z-index: 100000 !important; pointer-events: none;"></div>
                    </div>
                    <button id="close_btn" style="display: none; margin-top: 10px; width: 100%; padding: 10px; background-color: #555; color: white; border: none; border-radius: 4px; font-size: 14px; font-weight: bold;">❌ 關閉相機系統</button>
                </div>
                <style>#interactive video {width: 100% !important; height: 100% !important; object-fit: cover !important;} #interactive canvas {display: none !important;}</style>
                <script src="https://cdnjs.cloudflare.com/ajax/libs/quagga/0.12.1/quagga.min.js"></script>
                <script>
                    const barcodeDisplay = document.getElementById('barcode_display');
                    const scanBtn = document.getElementById('scan_btn');
                    const cameraArea = document.getElementById('interactive');
                    const closeBtn = document.getElementById('close_btn');
                    let lastResult = ""; let resultCount = 0;
                    barcodeDisplay.addEventListener('input', (e) => { window.parent.postMessage({type: 'streamlit:setComponentValue', value: e.target.value}, '*'); });
                    scanBtn.addEventListener('click', () => { cameraArea.style.display = 'block'; closeBtn.style.display = 'block'; lastResult = ""; resultCount = 0; Quagga.init({ inputStream : { name : "Live", type : "LiveStream", target: document.querySelector('#interactive'), constraints: { width: { min: 640, ideal: 1280 }, height: { min: 480, ideal: 960 }, facingMode: "environment" } }, locate: true, patchSize: "medium", halfSample: true, frequency: 4, decoder : { readers : ["code_128_reader", "ean_reader", "ean_8_reader", "code_39_reader"] } }, function(err) { if (err) { alert("鏡頭開門失敗！"); return; } Quagga.start(); }); });
                    Quagga.onDetected(function(data) { if(data.codeResult && data.codeResult.code) { let code = data.codeResult.code; if (code === lastResult) { resultCount++; if (resultCount >= 3) { barcodeDisplay.value = code; window.parent.postMessage({type: 'streamlit:setComponentValue', value: code}, '*'); Quagga.stop(); cameraArea.style.display = 'none'; closeBtn.style.display = 'none'; } } else { lastResult = code; resultCount = 1; } } });
                    closeBtn.addEventListener('click', () => { Quagga.stop(); cameraArea.style.display = 'none'; closeBtn.style.display = 'none'; });
                </script>
                """,
                height=380,
            )
            
            final_barcode = st.text_input("最終確認條碼", value=st.session_state.get('barcode_field', ''))

            st.markdown("---")
            ret_type = st.radio("選擇退貨形態", ["箱出", "散出"], horizontal=True)
            if ret_type == "箱出": qty, exp_date, quality, reason = 1, "", "良品", ""
            else:
                exp_date = st.text_input("輸入有效期限 (例: 202706)")
                qty = st.number_input("輸入數量", min_value=1, value=1)
                quality = st.radio("商品貨況", ["良品", "不良品"], horizontal=True)
                reason = ""
                if quality == "不良品": reason = st.selectbox("異常原因提示", ["", "外盒壓損", "外包裝污損", "內容物漏液", "過期品"])
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 儲存並繼續新增", use_container_width=True, type="primary"):
                    if not final_barcode: st.error("❌ 請先刷取或輸入條碼！")
                    elif ret_type == "散出" and not exp_date: st.error("❌ 散出必須填寫效期！")
                    else:
                        conn = get_db_connection()
                        today_str = datetime.now().strftime("%Y%m%d")
                        conn.execute("INSERT OR IGNORE INTO return_batches VALUES (?, ?, ?, '作業中')", (st.session_state['current_batch_id'], st.session_state['current_channel'], today_str))
                        seq = conn.execute("SELECT COUNT(*) FROM return_items WHERE batch_id = ?", (st.session_state['current_batch_id'],)).fetchone()[0] + 1
                        conn.execute('''INSERT INTO return_items (batch_id, item_seq, barcode, return_type, expiry_date, quantity, quality_status, damage_reason, operator) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', (st.session_state['current_batch_id'], seq, final_barcode, ret_type, exp_date, qty, quality, reason, st.session_state['username']))
                        conn.commit(); conn.close(); st.success(f"✅ 第 {seq} 筆商品成功儲存！"); st.rerun()
            with col2:
                if st.button("🚪 完成點收並離開", use_container_width=True):
                    if st.session_state['current_batch_id']:
                        conn = get_db_connection(); conn.execute("UPDATE return_batches SET status = '已完成' WHERE batch_id = ?", (st.session_state['current_batch_id'],)); conn.commit(); conn.close()
                    st.session_state['current_channel'] = ""; st.rerun()

   # --- 歷史紀錄分頁 (修正版) ---
    with tabs[1]:
        st.header("🔍 歷史紀錄與篩選")
        
        # 篩選區域
        with st.expander("📊 篩選查詢條件", expanded=True):
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1: start_date = st.date_input("起始日期", value=None)
            with col_f2: filter_barcode = st.text_input("篩選條碼")
            with col_f3: filter_op = st.text_input("篩選作業員")

        conn = get_db_connection()
        # 聯集查詢資料
        df = pd.read_sql_query("""
            SELECT b.create_date, i.* FROM return_items i 
            LEFT JOIN return_batches b ON i.batch_id = b.batch_id
        """, conn)
        conn.close()

        if not df.empty:
            # 1. 處理日期與欄位順序
            df['建檔日期'] = pd.to_datetime(df['create_date']).dt.strftime('%Y/%m/%d')
            # 調整欄位順序：將建檔日期放到最前面
            cols = ['建檔日期'] + [c for c in df.columns if c not in ['建檔日期', 'create_date']]
            df = df[cols]
            
            # 2. 處理條碼格式 (避免科學記號)
            df['barcode'] = df['barcode'].astype(str).apply(lambda x: f"'{x}")
            
            # 3. 執行篩選邏輯 (即時自動更新)
            if start_date:
                df = df[df['建檔日期'] >= start_date.strftime('%Y/%m/%d')]
            if filter_barcode:
                df = df[df['barcode'].str.contains(filter_barcode)]
            if filter_op:
                df = df[df['operator'].str.contains(filter_op)]
            
            # 4. 顯示表格 (use_container_width=True 同時隱藏預設的索引欄)
            st.dataframe(
                df.drop(columns=['create_date']), # 隱藏原始 create_date
                use_container_width=True, 
                hide_index=True # 關鍵參數：隱藏您紅框圈起來的那一欄索引
            )
            
            # 5. 下載報表
            st.download_button(
                label="📥 下載 XLSX 報表",
                data=to_excel(df.drop(columns=['create_date'])),
                file_name=f"退貨紀錄_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("尚無歷史單據。")
            )
        else: st.info("尚無歷史單據。")
