# 檔案名稱：app.py
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components

st.set_page_config(page_title="物流退貨點收系統", layout="centered")

# 💡 【核心設定】請在這裡輸入您的真實中文姓名！
ORIGINAL_ADMIN = "Admin999" 

# ==========================================
# 💡 雲端專用：防呆自動初始化資料庫
# ==========================================
def init_db_if_not_exists():
    conn = sqlite3.connect('return_system.db')
    cursor = conn.cursor()
    # 1. 建立使用者資料表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            register_date TEXT,
            role TEXT DEFAULT '一般用戶'
        )
    ''')
    # 2. 建立退貨批次主檔
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS return_batches (
            batch_id TEXT PRIMARY KEY,
            channel_name TEXT,
            create_date TEXT,
            status TEXT DEFAULT '作業中'
        )
    ''')
    # 3. 建立退貨商品明細檔
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
            operator TEXT,
            approval_status TEXT DEFAULT '已確認',
            new_quantity INTEGER,
            new_damage_reason TEXT
        )
    ''')
    conn.commit()
    conn.close()

# 每次網頁載入時都執行檢查，確保雲端廚房絕對有蓋好
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
if 'is_batch_saved' not in st.session_state: st.session_state['is_batch_saved'] = False

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
                    initial_role = "管理者" if reg_name == ORIGINAL_ADMIN or reg_name == "余宸緯" else "一般用戶"
                    conn.execute('INSERT INTO users (username, password, register_date, role) VALUES (?, ?, ?, ?)', 
                                 (reg_name, reg_pwd, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), initial_role))
                    conn.commit()
                    st.success(f"👍 【{reg_name}】註冊成功！身分：{initial_role}。請切換到[帳號登入]。")
                except sqlite3.IntegrityError: st.error("❌ 這個姓名已被註冊。")
                finally: conn.close()
            else: st.warning("⚠️ 欄位不能留空。")

# ==========================================
# 系統主頁面 (登入成功)
# ==========================================
else:
    st.sidebar.write(f"👤 作業員：**{st.session_state['username']}**")
    st.sidebar.write(f"🎖️ 權限：**{'管理者' if st.session_state['is_admin'] else '一般用戶'}**")
    if st.sidebar.button("登出系統"):
        st.session_state['logged_in'] = False
        st.session_state['username'] = ""
        st.session_state['is_admin'] = False
        st.session_state['current_channel'] = ""
        st.session_state['current_batch_id'] = ""
        st.session_state['is_batch_saved'] = False
        st.rerun()

    tabs_list = ["📦 退貨點收作業", "🔍 歷史紀錄與修改申請"]
    if st.session_state['is_admin']: 
        tabs_list.append("🔔 主管修改批核")
        tabs_list.append("👥 員工權限與離職維護")
        
    tabs = st.tabs(tabs_list)
    
    # --- 分頁一：退貨點收作業 ---
    with tabs[0]:
        if st.session_state['current_channel'] == "":
            st.subheader("🚀 請設定本次作業環境與通路")
            
            if st.session_state['is_admin']:
                env_choice = st.radio("⚙️ 請選擇作業環境", ["正式環境", "測試環境"], horizontal=True)
            else:
                env_choice = "正式環境"
                st.info("🔒 系統目前鎖定在：**正式環境**")
                
            selected_chan = st.selectbox("🏬 選擇退貨通路", ["請選擇...", "MOMO", "寶雅", "康是美", "屈臣氏"])
            
            if st.button("鎖定並開始作業", use_container_width=True):
                if selected_chan != "請選擇...":
                    st.session_state['current_channel'] = selected_chan
                    st.session_state['current_env'] = env_choice
                    st.session_state['is_batch_saved'] = False 
                    
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
            st.info(f"🏬 通路：**{st.session_state['current_channel']}** ｜ 🧾 預計批號：**{st.session_state['current_batch_id']}**")
            
            st.markdown("**🔍 商品條碼登錄**")
            components.html(
                """
                <div style="display: flex; gap: 8px; align-items: center; font-family: sans-serif;">
                    <input type="text" id="barcode_display" placeholder="請手動輸入或使用藍牙槍掃描" 
                           style="flex: 1; padding: 10px; font-size: 16px; border: 1px solid #ccc; border-radius: 4px;">
                    <button id="scan_btn" style="padding: 10px 16px; font-size: 16px; background-color: #ff4b4b; color: white; border: none; border-radius: 4px; cursor: pointer; display: flex; align-items: center; gap: 4px;">
                        📷 掃碼
                    </button>
                </div>
                
                <div id="camera_modal" style="display: none; position: fixed; top:0; left:0; width:100vw; height:100vh; background: rgba(0,0,0,0.9); z-index: 99999; flex-direction: column; justify-content: center; align-items: center;">
                    <div style="position: relative; width: 85%; max-width: 360px;">
                        <div id="interactive" class="viewport" style="width: 100%; border: 2px solid #fff; border-radius: 8px; overflow: hidden;"></div>
                        <div style="position: absolute; top: 50%; left: 5%; width: 90%; height: 2px; background-color: red; box-shadow: 0 0 8px red; pointer-events: none;"></div>
                    </div>
                    <p style="color: white; margin-top: 15px; font-size: 14px;">請將紅色線對準商品條碼</p>
                    <button id="close_cam" style="margin-top: 10px; padding: 8px 16px; background: #666; color: white; border: none; border-radius: 4px;">❌ 關閉相機</button>
                </div>

                <script src="https://cdnjs.cloudflare.com/ajax/libs/quagga/0.12.1/quagga.min.js"></script>
                <script>
                    const barcodeDisplay = document.getElementById('barcode_display');
                    const scanBtn = document.getElementById('scan_btn');
                    const cameraModal = document.getElementById('camera_modal');
                    const closeCam = document.getElementById('close_cam');

                    barcodeDisplay.addEventListener('input', (e) => {
                        window.parent.postMessage({type: 'streamlit:setComponentValue', value: e.target.value}, '*');
                    });

                    scanBtn.addEventListener('click', () => {
                        cameraModal.style.display = 'flex';
                        Quagga.init({
                            inputStream : {
                                name : "Live",
                                type : "LiveStream",
                                target: document.querySelector('#interactive'),
                                constraints: { width: 480, height: 320, facingMode: "environment" }
                            },
                            decoder : { readers : ["code_128_reader", "ean_reader", "ean_8_reader", "code_39_reader"] }
                        }, function(err) {
                            if (err) { alert("相機啟動失敗！"); cameraModal.style.display = 'none'; return; }
                            Quagga.start();
                        });
                    });

                    Quagga.onDetected(function(data) {
                        if(data.codeResult && data.codeResult.code) {
                            let code = data.codeResult.code;
                            barcodeDisplay.value = code;
                            window.parent.postMessage({type: 'streamlit:setComponentValue', value: code}, '*');
                            Quagga.stop();
                            cameraModal.style.display = 'none';
                        }
                    });

                    closeCam.addEventListener('click', () => {
                        Quagga.stop();
                        cameraModal.style.display = 'none';
                    });
                </script>
                """, height=65,
            )
            
            barcode_input = st.session_state.get('barcode_field', '')
            if barcode_input:
                st.success(f"📥 目前帶入條碼：**{barcode_input}**")

            st.markdown("---")
            ret_type = st.radio("選擇退貨形態", ["箱出", "散出"], horizontal=True)
            
            if ret_type == "箱出":
                qty, exp_date, quality, reason = 1, "", "良品", ""
                st.caption("💡 箱出模式：數量鎖定為 1，免填效期與貨況。")
            else:
                exp_date = st.text_input("輸入有效期限 (例: 202706)")
                qty = st.number_input("輸入數量", min_value=1, value=1)
                quality = st.radio("商品貨況", ["良品", "不良品"], horizontal=True)
                reason = ""
                if quality == "不良品":
                    reason_suggestions = ["外盒壓損", "外包裝污損", "內容物漏液", "過期品"]
                    reason = st.selectbox("異常原因提示", [""] + reason_suggestions)
                    custom_reason = st.text_input("手動輸入異常原因")
                    if custom_reason: reason = custom_reason
                    st.file_uploader("📸 拍攝不良品照片", type=["jpg", "png"])
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 儲存並繼續新增", use_container_width=True, type="primary"):
                    if not barcode_input: st.error("❌ 請先刷取或輸入條碼！")
                    elif ret_type == "散出" and not exp_date: st.error("❌ 散出必須填寫效期！")
                    else:
                        conn = get_db_connection()
                        if not st.session_state['is_batch_saved']:
                            today_str = datetime.now().strftime("%Y%m%d")
                            conn.execute("INSERT OR IGNORE INTO return_batches VALUES (?, ?, ?, '作業中')", 
                                         (st.session_state['current_batch_id'], st.session_state['current_channel'], today_str))
                            st.session_state['is_batch_saved'] = True
                        
                        seq = conn.execute("SELECT COUNT(*) FROM return_items WHERE batch_id = ?", (st.session_state['current_batch_id'],)).fetchone()[0] + 1
                        conn.execute('''INSERT INTO return_items (batch_id, item_seq, barcode, return_type, expiry_date, quantity, quality_status, damage_reason, operator, approval_status)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '已確認')''', 
                                     (st.session_state['current_batch_id'], seq, barcode_input, ret_type, exp_date, qty, quality, reason, st.session_state['username']))
                        conn.commit()
                        conn.close()
                        
                        st.success(f"✅ 第 {seq} 筆商品成功儲存！")
                        st.rerun()
            with col2:
                leave_btn_label = "🚪 完成點收並離開" if st.session_state['is_batch_saved'] else "↩️ 放棄作業(未登入任何貨)"
                if st.button(leave_btn_label, use_container_width=True):
                    if st.session_state['is_batch_saved']:
                        conn = get_db_connection()
                        conn.execute("UPDATE return_batches SET status = '已完成' WHERE batch_id = ?", (st.session_state['current_batch_id'],))
                        conn.commit()
                        conn.close()
                    st.session_state['current_channel'], st.session_state['current_batch_id'] = "", ""
                    st.session_state['is_batch_saved'] = False
                    st.rerun()

    # --- 分頁二：歷史紀錄與修改申請 ---
    with tabs[1]:
        st.header("🔍 歷史紀錄與修改維護")
        st.subheader("設定篩選條件")
        c1, c2, c3 = st.columns(3)
        with c1: s_batch = st.text_input("批次單號查詢")
        with c2: s_barcode = st.text_input("商品條碼查詢")
        with c3: s_operator = st.text_input("作業員姓名查詢")
        
        conn = get_db_connection()
        if st.session_state['is_admin']:
            query = "SELECT * FROM return_items WHERE 1=1"
            params = []
        else:
            query = "SELECT * FROM return_items WHERE batch_id NOT LIKE 'TEST%'"
            params = []
            
        if s_batch: query += " AND batch_id LIKE ?"; params.append(f"%{s_batch}%")
        if s_barcode: query += " AND barcode LIKE ?"; params.append(f"%{s_barcode}%")
        if s_operator: query += " AND operator LIKE ?"; params.append(f"%{s_operator}%")
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        if not df.empty:
            st.dataframe(df[["id", "batch_id", "item_seq", "barcode", "return_type", "expiry_date", "quantity", "quality_status", "damage_reason", "operator", "approval_status"]], use_container_width=True)
            
            if st.session_state['is_admin']:
                st.download_button(label="📥 下載此篩選結果明細 Excel", data=open('return_system.db', 'rb'), file_name=f"退貨報表_{datetime.now().strftime('%Y%m%d')}.xlsx", mime="application/vnd.ms-excel", use_container_width=True)
            
            st.subheader("✏️ 發起數據修改申請")
            edit_id = st.number_input("請輸入要修改的資料行數 ID", min_value=1, step=1)
            new_q = st.number_input("修正後的正確數量", min_value=1, value=1)
            new_r = st.text_input("修正原因備註")
            
            if st.button("送出修改申請", use_container_width=True):
                conn = get_db_connection()
                check = conn.execute("SELECT * FROM return_items WHERE id = ?", (edit_id,)).fetchone()
                if check:
                    conn.execute("UPDATE return_items SET approval_status = '審核中', new_quantity = ?, new_damage_reason = ? WHERE id = ?", (new_q, new_r, edit_id))
                    conn.commit()
                    st.success("📢 修改申請已送出！請口頭回報主管審核。")
                else: st.error("❌ 找不到該筆資料 ID。")
                conn.close()
        else: st.info("查無退貨紀錄。")

    # --- 分頁三：主管修改批核 ---
    if st.session_state['is_admin']:
        with tabs[2]:
            st.header("🔔 主管審核工作台")
            conn = get_db_connection()
            review_df = pd.read_sql_query("SELECT id, batch_id, item_seq, barcode, quantity AS 原數量, new_quantity AS 申請修改數量, damage_reason AS 原原因, new_damage_reason AS 申請修改原因, operator FROM return_items WHERE approval_status = '審核中'", conn)
            conn.close()
            
            if not review_df.empty:
                st.dataframe(review_df, use_container_width=True)
                app_id = st.number_input("輸入欲處理的審核單 ID", min_value=1, step=1)
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("🟢 同意修改", use_container_width=True, type="primary"):
                        conn = get_db_connection()
                        conn.execute("UPDATE return_items SET quantity = new_quantity, damage_reason = new_damage_reason, approval_status = '已確認' WHERE id = ?", (app_id,))
                        conn.commit(); conn.close()
                        st.success("已核准變更！"); st.rerun()
                with col_btn2:
                    if st.button("🔴 駁回申請", use_container_width=True):
                        conn = get_db_connection()
                        conn.execute("UPDATE return_items SET approval_status = '已確認' WHERE id = ?", (app_id,))
                        conn.commit(); conn.close()
                        st.success("已駁回申請。"); st.rerun()
            else: st.success("🎉 目前暫無等待審核的異常數據。")

    # --- 分頁四：員工權限與離職維護 ---
    if st.session_state['is_admin']:
        with tabs[3]:
            st.header("👥 員工帳號與權限維護中心")
            conn = get_db_connection()
            users_df = pd.read_sql_query("SELECT username AS 中文姓名, register_date AS 註冊日期, role AS 目前身分 FROM users", conn)
            conn.close()
            
            st.dataframe(users_df, use_container_width=True)
            st.markdown("---")
            st.subheader("🛠️ 帳號異動操作")
            target_user = st.text_input("請輸入要操作的員工【中文姓名】").strip()
            
            c_role1, c_role2, c_delete = st.columns(3)
            with c_role1:
                if st.button("🎖️ 升職為管理者", use_container_width=True):
                    if target_user:
                        conn = get_db_connection()
                        conn.execute("UPDATE users SET role = '管理者' WHERE username = ?", (target_user,))
                        conn.commit(); conn.close()
                        st.success(f"已將 【{target_user}】 提升為管理者權限！"); st.rerun()
            with c_role2:
                if st.button("👤 降職為一般用戶", use_container_width=True):
                    if target_user:
                        if target_user == ORIGINAL_ADMIN: st.error("❌ 您不能降職自己！")
                        else:
                            conn = get_db_connection()
                            conn.execute("UPDATE users SET role = '一般用戶' WHERE username = ?", (target_user,))
                            conn.commit(); conn.close()
                            st.success(f"已將 【{target_user}】 降為一般作業員。"); st.rerun()
            with c_delete:
                if st.button("❌ 刪除此用戶(離職)", use_container_width=True):
                    if target_user:
                        if target_user == ORIGINAL_ADMIN: st.error("❌ 您不能刪除自己！")
                        else:
                            conn = get_db_connection()
                            conn.execute("DELETE FROM users WHERE username = ?", (target_user,))
                            conn.commit(); conn.close()
                            st.success(f"🔥 已成功刪除離職員工【{target_user}】！"); st.rerun()
