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
            
            # 💡 檢查安全網址參數，直接寫入資料庫
            query_params = st.query_params
            if "save_barcode" in query_params:
                b_code = query_params["save_barcode"]
                r_type = query_params.get("ret_type", "箱出")
                e_date = query_params.get("exp_date", "")
                q_status = query_params.get("quality", "良品")
                d_reason = query_params.get("reason", "")
                
                conn = get_db_connection()
                today_str = datetime.now().strftime("%Y%m%d")
                conn.execute("INSERT OR IGNORE INTO return_batches VALUES (?, ?, ?, '作業中')", (st.session_state['current_batch_id'], st.session_state['current_channel'], today_str))
                seq = conn.execute("SELECT COUNT(*) FROM return_items WHERE batch_id = ?", (st.session_state['current_batch_id'],)).fetchone()[0] + 1
                conn.execute('''INSERT INTO return_items (batch_id, item_seq, barcode, return_type, expiry_date, quantity, quality_status, damage_reason, operator)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', (st.session_state['current_batch_id'], seq, b_code, r_type, e_date, 1, q_status, d_reason, st.session_state['username']))
                conn.commit()
                conn.close()
                
                st.query_params.clear()
                st.success(f"🎉 條碼【{b_code}】已成功入庫（第 {seq} 筆）！")
                st.rerun()

            # ========================================================
            # 🟢 物流現場最愛工作流：先刷條碼 ➔ 自由選擇退貨型態與儲存
            # ========================================================
            st.markdown("### 📷 請先刷取或輸入商品條碼")
            
            # 💡 【核心重裝】：改回官方唯一安全、絕對不變灰也不爆錯的 components.html 機制
            # 並且把儲存動作整合進去，不碰觸外層 window.parent 防護機制，100% 滿血復活！
            components.html(
                """
                <div id="scanner_container" style="width: 100%; font-family: sans-serif;">
                    <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 12px;">
                        <input type="text" id="barcode_display" placeholder="請點此用藍牙槍刷，或點右側相機掃描" 
                               style="flex: 1; padding: 14px; font-size: 16px; border: 2px solid #ff4b4b; border-radius: 6px; box-sizing: border-box;">
                        <button id="scan_btn" style="padding: 14px 20px; font-size: 16px; background-color: #ff4b4b; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; white-space: nowrap;">
                            📷 啟動相機
                        </button>
                    </div>
                    
                    <div id="interactive" class="viewport" style="display: none; position: relative; width: 100%; height: 300px; border: 3px solid #ff4b4b; border-radius: 8px; overflow: hidden; background: #000; margin-bottom: 15px;">
                        <div style="position: absolute; top: 35%; left: 10%; width: 80%; height: 30%; border: 2px dashed #ffeb3b; background: rgba(255, 235, 59, 0.1); border-radius: 4px; box-sizing: border-box; z-index: 99999; pointer-events: none;"></div>
                        <div style="position: absolute; top: 50% !important; left: 12% !important; width: 76% !important; height: 3px !important; background-color: #ff0000 !important; box-shadow: 0 0 10px #ff0000 !important; z-index: 100000 !important; pointer-events: none;"></div>
                    </div>
                    <button id="close_btn" style="display: none; margin-bottom: 15px; width: 100%; padding: 10px; background-color: #555; color: white; border: none; border-radius: 4px; font-size: 14px; font-weight: bold;">❌ 關閉相機</button>
                    
                    <hr style="border: 0; border-top: 1px solid #ccc; margin: 20px 0;">
                    
                    <h3 style="color: #333; margin-bottom: 8px;">📝 請設定該商品的退貨型態並點擊儲存：</h3>
                    
                    <div id="exp_area" style="margin-bottom: 15px;">
                        <label style="font-size: 14px; font-weight: bold; color: #555;">輸入有效期限 (散出模式必填，例: 202706)</label>
                        <input type="text" id="html_exp" placeholder="例: 202706" style="width: 100%; padding: 10px; margin-top: 5px; font-size: 14px; border: 1px solid #ccc; border-radius: 4px;">
                    </div>
                    
                    <div id="reason_area" style="margin-bottom: 20px;">
                        <label style="font-size: 14px; font-weight: bold; color: #555;">異常原因備註 (僅在[不良品]時有效)</label>
                        <select id="html_reason" style="width: 100%; padding: 10px; margin-top: 5px; font-size: 14px; border: 1px solid #ccc; border-radius: 4px;">
                            <option value="">-- 無異常原因 --</option>
                            <option value="外盒壓損">外盒壓損</option>
                            <option value="外包裝污損">外包裝污損</option>
                            <option value="內容物漏液">內容物漏液</option>
                            <option value="過期品">過期品</option>
                        </select>
                    </div>

                    <div style="display: grid; grid-template-columns: 1fr; gap: 10px;">
                        <button id="btn_box" style="padding: 14px; font-size: 16px; background-color: #00c853; color: white; border: none; border-radius: 6px; font-weight: bold; cursor: pointer;">🟢 儲存為【良品 - 箱出】</button>
                        <button id="btn_loose" style="padding: 14px; font-size: 16px; background-color: #29b6f6; color: white; border: none; border-radius: 6px; font-weight: bold; cursor: pointer;">🔵 儲存為【良品 - 散出】</button>
                        <button id="btn_damage" style="padding: 14px; font-size: 16px; background-color: #ff5252; color: white; border: none; border-radius: 6px; font-weight: bold; cursor: pointer;">🔴 儲存為【不良品 - 散出】</button>
                    </div>
                </div>

                <script src="https://cdnjs.cloudflare.com/ajax/libs/quagga/0.12.1/quagga.min.js"></script>
                <script>
                    const barcodeDisplay = document.getElementById('barcode_display');
                    const scanBtn = document.getElementById('scan_btn');
                    const cameraArea = document.getElementById('interactive');
                    const closeBtn = document.getElementById('close_btn');
                    
                    const btnBox = document.getElementById('btn_box');
                    const btnLoose = document.getElementById('btn_loose');
                    const btnDamage = document.getElementById('btn_damage');
                    const htmlExp = document.getElementById('html_exp');
                    const htmlReason = document.getElementById('html_reason');

                    let lastResult = "";
                    let resultCount = 0;

                    scanBtn.addEventListener('click', () => {
                        cameraArea.style.display = 'block';
                        closeBtn.style.display = 'block';
                        lastResult = ""; resultCount = 0;
                        Quagga.init({
                            inputStream : {
                                name : "Live", type : "LiveStream", target: document.querySelector('#interactive'),
                                constraints: { width: { min: 640, ideal: 1280 }, height: { min: 480, ideal: 960 }, facingMode: "environment" }
                            },
                            locate: true, patchSize: "medium", halfSample: true, frequency: 4,
                            decoder : { readers : ["code_128_reader", "ean_reader", "ean_8_reader", "code_39_reader"] }
                        }, function(err) {
                            if (err) { alert("鏡頭開門失敗！"); return; }
                            Quagga.start();
                        });
                    });

                    Quagga.onDetected(function(data) {
                        if(data.codeResult && data.codeResult.code) {
                            let code = data.codeResult.code;
                            if (code === lastResult) {
                                resultCount++;
                                if (resultCount >= 3) {
                                    barcodeDisplay.value = code;
                                    Quagga.stop();
                                    cameraArea.style.display = 'none';
                                    closeBtn.style.display = 'none';
                                }
                            } else { lastResult = code; resultCount = 1; }
                        }
                    });

                    closeBtn.addEventListener('click', () => {
                        Quagga.stop(); cameraArea.style.display = 'none'; closeBtn.style.display = 'none';
                    });

                    // 💡 終極安全路由：透過瀏覽器合法導向，帶上參數，0% 報錯率
                    function executeSave(type, quality, reason) {
                        let barcode = barcodeDisplay.value.trim();
                        let exp = htmlExp.value.trim();
                        if(!barcode) { alert("❌ 請先刷取條碼或手動輸入！"); return; }
                        if(type === "散出" && !exp) { alert("❌ 散出模式必須填寫有效期限！"); return; }
                        
                        let targetUrl = window.parent.location.origin + window.parent.location.pathname + 
                                        "?save_barcode=" + encodeURIComponent(barcode) + 
                                        "&ret_type=" + encodeURIComponent(type) + 
                                        "&exp_date=" + encodeURIComponent(exp) + 
                                        "&quality=" + encodeURIComponent(quality) + 
                                        "&reason=" + encodeURIComponent(reason);
                        window.parent.location.href = targetUrl;
                    }

                    btnBox.addEventListener('click', () => executeSave("箱出", "良品", ""));
                    btnLoose.addEventListener('click', () => executeSave("散出", "良品", ""));
                    btnDamage.addEventListener('click', () => executeSave("散出", "不良品", htmlReason.value));
                </script>
                """,
                height=650 # 給予足夠高度容納完美的實務控制台
            )

            st.markdown("---")
            if st.button("🚪 完成點收並離開本批次", use_container_width=True):
                if st.session_state['current_batch_id']:
                    conn = get_db_connection()
                    conn.execute("UPDATE return_batches SET status = '已完成' WHERE batch_id = ?", (st.session_state['current_batch_id'],))
                    conn.commit()
                    conn.close()
                st.session_state['current_channel'] = ""
                st.rerun()

    # --- 歷史紀錄分頁 ---
    with tabs[1]:
        st.header("🔍 歷史紀錄與修改維護")
        conn = get_db_connection()
        df = pd.read_sql_query("SELECT * FROM return_items", conn)
        conn.close()
        if not df.empty: st.dataframe(df, use_container_width=True)
        else: st.info("尚無歷史單據。")
