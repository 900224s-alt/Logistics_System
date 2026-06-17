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
    # 建立資料表 (確保有 status 欄位)
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, register_date TEXT, role TEXT, status TEXT)''')
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
if 'is_batch_saved' not in st.session_state: st.session_state['is_batch_saved'] = False

st.title("📦 物流退貨點收系統")

if not st.session_state['logged_in']:
    tab1, tab2 = st.tabs(["👤 帳號登入", "📝 申請註冊帳號"])
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
                    if user['status'] == 'Active':
                        st.session_state['logged_in'] = True
                        st.session_state['username'] = login_name
                        st.session_state['is_admin'] = (user['role'] == "管理者" or login_name == ORIGINAL_ADMIN)
                        st.success(f"🎉 歡迎【{login_name}】上工。")
                        st.rerun()
                    else:
                        st.warning("⚠️ 帳號申請審核中，請聯繫管理員。")
                else: st.error("❌ 姓名或密碼錯誤。")
            else: st.warning("⚠️ 請輸入姓名與密碼。")
    with tab2:
        st.subheader("申請註冊帳號")
        reg_name = st.text_input("請輸入你的中文真實姓名", key="reg_name").strip()
        reg_pwd = st.text_input("自訂密碼", type="password", key="reg_pwd")
        if st.button("送出申請", use_container_width=True):
            if reg_name and reg_pwd:
                conn = get_db_connection()
                try:
                    conn.execute('INSERT INTO users (username, password, register_date, role, status) VALUES (?, ?, ?, ?, ?)', 
                                 (reg_name, reg_pwd, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "一般用戶", "Pending"))
                    conn.commit()
                    st.success("👍 申請已送出，請等待管理員核准後方可登入。")
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
            st.subheader("🚀 請設定本次作業環境與通路")
            env_choice = st.radio("⚙️ 請選擇作業環境", ["正式環境", "測試環境"], horizontal=True) if st.session_state['is_admin'] else "正式環境"
            selected_chan = st.selectbox("🏬 選擇退貨通路", ["請選擇...", "MOMO", "寶雅", "康是美", "屈臣氏", "蝦皮", "家購", "大智通", "好市多","PCHPME","松本清","唐吉訶德"])
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
            st.info(f"🏬 通路：**{st.session_state['current_channel']}** ｜ 🧾 批號：**{st.session_state['current_batch_id']}**")
            barcode_input = st.text_input("🔍 請刷取商品條碼或手動輸入", key="barcode_field")
            if barcode_input: st.success(f"📥 目前帶入條碼：**{barcode_input}**")
            st.markdown("---")
            ret_type = st.radio("選擇退貨形態", ["箱出", "散出"], horizontal=True)
            qty, exp_date, quality, selected_reasons = 1, "", "良品", []
            
            if ret_type == "散出":
                exp_date = st.text_input("輸入有效期限 (例: 202706)")
                qty = st.number_input("輸入數量", min_value=1, value=1)
                quality = st.radio("商品貨況", ["良品", "不良品"], horizontal=True)
                if quality == "不良品":
                    selected_reasons = st.multiselect("勾選不良品原因", DAMAGE_REASONS)
                    reason = ", ".join(selected_reasons)
                else:
                    reason = ""
            
            if st.button("💾 儲存並繼續新增", use_container_width=True, type="primary"):
                conn = get_db_connection()
                if not st.session_state['is_batch_saved']:
                    conn.execute("INSERT OR IGNORE INTO return_batches VALUES (?, ?, ?, '作業中')", (st.session_state['current_batch_id'], st.session_state['current_channel'], datetime.now().strftime("%Y%m%d")))
                    st.session_state['is_batch_saved'] = True
                created_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                conn.execute('''INSERT INTO return_items (batch_id, barcode, return_type, expiry_date, quantity, quality_status, damage_reason, operator, approval_status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, '已確認', ?)''', 
                            (st.session_state['current_batch_id'], barcode_input, ret_type, exp_date, qty, quality, reason, st.session_state['username'], created_time))
                conn.commit(); conn.close(); st.success("✅ 儲存成功！"); st.rerun()

    with tabs[1]:
        st.header("🔍 歷史紀錄與修改申請")
        with st.expander("⚙️ 篩選條件設定", expanded=True):
            c1, c2 = st.columns(2)
            s_start = c1.date_input("開始日期", value=None)
            s_end = c2.date_input("結束日期", value=None)
            s_batch = st.text_input("退貨單號 (批號)")
            c3, c4, c5 = st.columns(3)
            s_barcode = c3.text_input("商品條碼")
            s_operator = c4.text_input("作業員")
            s_type = c5.multiselect("形態", ["箱出", "散出"])
            c6, c7 = st.columns(2)
            s_channel = c6.multiselect("通路", ["MOMO", "寶雅", "康是美", "屈臣氏", "蝦皮", "家購", "大智通", "好市多","PCHPME","松本清","唐吉訶德"])
            s_quality = c7.multiselect("貨況", ["良品", "不良品"])
            
            if st.button("查詢數據"):
                conn = get_db_connection()
                query = "SELECT i.*, b.channel FROM return_items i LEFT JOIN return_batches b ON i.batch_id = b.batch_id WHERE 1=1"
                params = []
                if s_start: query += " AND i.created_at >= ?"; params.append(f"{s_start}")
                if s_end: query += " AND i.created_at <= ?"; params.append(f"{s_end} 23:59:59")
                if s_batch: query += " AND i.batch_id LIKE ?"; params.append(f"%{s_batch}%")
                if s_barcode: query += " AND i.barcode LIKE ?"; params.append(f"%{s_barcode}%")
                if s_operator: query += " AND i.operator LIKE ?"; params.append(f"%{s_operator}%")
                if s_type:
                    query += f" AND i.return_type IN ({','.join(['?']*len(s_type))})"
                    params.extend(s_type)
                if s_channel:
                    query += f" AND b.channel IN ({','.join(['?']*len(s_channel))})"
                    params.extend(s_channel)
                if s_quality:
                    query += f" AND i.quality_status IN ({','.join(['?']*len(s_quality))})"
                    params.extend(s_quality)
                if not st.session_state['is_admin']: query += " AND i.batch_id NOT LIKE 'TEST%'"
                
                df = pd.read_sql_query(query, conn, params=params); conn.close()
                st.session_state['df'] = df

        if 'df' in st.session_state and not st.session_state['df'].empty:
            df = st.session_state['df'].copy()
            df.rename(columns={'channel': '通路'}, inplace=True)
            dt = pd.to_datetime(df["created_at"])
            df.insert(0, "建立日期", dt.dt.strftime('%Y-%m-%d'))
            cols = ['建立日期', '通路'] + [c for c in df.columns if c not in ['建立日期', '通路', 'item_seq', 'created_at']]
            df = df.reindex(columns=cols)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            st.subheader("🛠️ 資料更正操作")
            target_id = st.number_input("輸入要更正的資料 ID", min_value=1, step=1)
            action = st.selectbox("選擇操作動作", ["請選擇...", "修改數量", "轉換貨況", "申請刪除資料"])
            
            if action == "修改數量":
                val = st.number_input("輸入正確數量", min_value=1, value=1)
                if st.button("確認送出修改申請"):
                    conn = get_db_connection()
                    conn.execute("UPDATE return_items SET quantity = ?, approval_status = '審核中' WHERE id = ?", (val, target_id))
                    conn.commit(); conn.close(); st.success("已提交修改申請，請至主管批核處確認。"); st.rerun()
            elif action == "轉換貨況":
                new_q = st.radio("變更為", ["良品", "不良品"], horizontal=True)
                qty_conv = st.number_input("輸入需轉換的數量", min_value=1, value=1)
                if st.button("確認提交轉換"):
                    conn = get_db_connection()
                    conn.execute("UPDATE return_items SET quality_status = ?, quantity = ?, approval_status = '審核中' WHERE id = ?", (new_q, qty_conv, target_id))
                    conn.commit(); conn.close(); st.success("已提交貨況轉換申請，請至主管批核處確認。"); st.rerun()
            elif action == "申請刪除資料":
                if st.button("⚠️ 確認申請刪除此筆數據"):
                    conn = get_db_connection()
                    conn.execute("UPDATE return_items SET approval_status = '申請刪除' WHERE id = ?", (target_id,))
                    conn.commit(); conn.close(); st.warning("刪除申請已送出，等待主管確認。"); st.rerun()
        else: st.info("無紀錄，請點擊查詢。")

    with tabs[2]:
        st.header("🔔 主管修改批核")
        if st.session_state['is_admin']:
            st.subheader("🔔 待審核帳號註冊")
            conn = get_db_connection()
            pending = pd.read_sql_query("SELECT id, username, register_date FROM users WHERE status = 'Pending'", conn)
            st.dataframe(pending, use_container_width=True)
            uid = st.number_input("輸入要核准的用戶 ID", min_value=1, step=1)
            role_sel = st.selectbox("核准身分", ["一般用戶", "管理者"])
            if st.button("🟢 核准此帳號註冊"):
                conn.execute("UPDATE users SET status = 'Active', role = ? WHERE id = ?", (role_sel, uid))
                conn.commit(); conn.close(); st.success("已啟用！"); st.rerun()
            
            st.markdown("---")
            st.subheader("更正與刪除審核")
            review_df = pd.read_sql_query("SELECT * FROM return_items WHERE approval_status IN ('審核中', '申請刪除')", conn)
            conn.close()
            if not review_df.empty:
                st.dataframe(review_df, use_container_width=True)
                app_id = st.number_input("輸入欲處理的審核單 ID", min_value=1, step=1)
                c_a, c_b = st.columns(2)
                if c_a.button("🟢 同意變更"):
                    conn = get_db_connection()
                    status = conn.execute("SELECT approval_status FROM return_items WHERE id = ?", (app_id,)).fetchone()
                    if status and status[0] == '申請刪除':
                        conn.execute("DELETE FROM return_items WHERE id = ?", (app_id,))
                    else:
                        conn.execute("UPDATE return_items SET approval_status = '已確認' WHERE id = ?", (app_id,))
                    conn.commit(); conn.close(); st.success("處理成功！"); st.rerun()
                if c_b.button("🔴 駁回申請"):
                    conn = get_db_connection(); conn.execute("UPDATE return_items SET approval_status = '已確認' WHERE id = ?", (app_id,)); conn.commit(); conn.close(); st.rerun()
            else: st.info("目前無待審核案件。")
        else: st.error("僅管理員可訪問")

    with tabs[3]:
        st.header("👥 員工權限與離職維護")
        if st.session_state['is_admin']:
            conn = get_db_connection()
            users_df = pd.read_sql_query("SELECT username AS 中文姓名, register_date AS 註冊日期, role AS 目前身分, status AS 狀態 FROM users", conn)
            conn.close()
            st.dataframe(users_df, use_container_width=True)
            st.markdown("---")
            target_user = st.text_input("請輸入要操作的員工姓名").strip()
            c1, c2, c3 = st.columns(3)
            if c1.button("🎖️ 升職為管理者"):
                conn = get_db_connection(); conn.execute("UPDATE users SET role = '管理者' WHERE username = ?", (target_user,)); conn.commit(); conn.close(); st.rerun()
            if c2.button("👤 降職為一般用戶"):
                conn = get_db_connection(); conn.execute("UPDATE users SET role = '一般用戶' WHERE username = ?", (target_user,)); conn.commit(); conn.close(); st.rerun()
            if c3.button("❌ 刪除此用戶"):
                conn = get_db_connection(); conn.execute("DELETE FROM users WHERE username = ?", (target_user,)); conn.commit(); conn.close(); st.rerun()
        else: st.error("您沒有管理權限。")
