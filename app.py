import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

def get_tw_now():
    return datetime.utcnow() + timedelta(hours=8)

CHANNEL_CODES = {
    "MOMO": "MOMO", "寶雅": "POYA", "康是美": "COSMED", "屈臣氏": "WATSONS", 
    "蝦皮": "SHOPEE", "家購": "JIAGO", "大智通": "DZT", "好市多": "COSTCO", 
    "PCHPME": "PCHOME", "松本清": "MATSUKIYO", "唐吉訶德": "DONKI"
}

# --- 條碼提醒需求 ---
BARCODE_ALERTS = {
    "4710155288739": ["勿拆成單品單件"],
    "4710155287558": ["勿拆成單品單件"],
    "4710155284779": ["請額外裝箱並貼上大字報（好壞品分開放）"],
    "4710155285837": ["請額外裝箱並貼上大字報（好壞品分開放）"],
    "4710155281877": ["請額外裝箱並貼上大字報（好壞品分開放）"],
    "4710155274527": ["請額外裝箱並貼上大字報（好壞品分開放）"],
    "4710155282249": ["需退回工廠商品，請額外裝箱並貼上大字報（好壞品分開放）"],
    "4710155277528": ["需退回工廠商品，請額外裝箱並貼上大字報（好壞品分開放）"],
    "4710155279522": ["需退回工廠商品，請額外裝箱並貼上大字報（好壞品分開放）"],
    "4710155277573": ["需退回工廠商品，請額外裝箱並貼上大字報（好壞品分開放）"],
    "4710155282188": ["需退回工廠商品，請額外裝箱並貼上大字報（好壞品分開放）"],
    "4710155285653": ["需退回工廠商品，請額外裝箱並貼上大字報（好壞品分開放）"],
    "4710155285912": ["需退回工廠商品，請額外裝箱並貼上大字報（好壞品分開放）"],
    "4710155278921": ["需退回工廠商品，請額外裝箱並貼上大字報（好壞品分開放）"],
    "4710155282386": ["需退回工廠商品，請額外裝箱並貼上大字報（好壞品分開放）"],
    "4710155278860": ["需退回工廠商品，請額外裝箱並貼上大字報（好壞品分開放）"]
}

# --- 莫蘭迪配色設定 ---
st.markdown("""
<style>
    div.stButton > button[kind="primary"] { background-color: #8da3b4 !important; border: none !important; color: white !important; }
    div.stButton > button#back-btn { background-color: #d4c4a8 !important; border: none !important; color: white !important; }
    div.stButton > button#close-btn { background-color: #c48b8b !important; border: none !important; color: white !important; }
</style>
""", unsafe_allow_html=True)

ORIGINAL_ADMIN = "余宸緯"
DAMAGE_REASONS = ["盒凹", "嚴重盒凹", "盒污", "劃痕", "防盜貼", "已過期（一個月內）", "即期（兩個月內）", "短效（半年內）", "效期模糊", "批號模糊", "已開封", "已開封使用", "空盒", "膠膜破損", "膠膜嚴重破損", "膠膜污損", "色差", "漸層色差", "嚴重色差", "霧氣", "漏液", "嚴重漏液", "外盒有貼標籤", "外膜有貼標籤", "外膜有貼膠帶+盒內有貼標籤", "外盒有貼膠帶+盒內有貼標籤"]

def get_db_connection():
    conn = sqlite3.connect('return_system.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, register_date TEXT, role TEXT)")
    try: cursor.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'pending'")
    except: pass
    cursor.execute("CREATE TABLE IF NOT EXISTS return_batches (batch_id TEXT PRIMARY KEY, channel TEXT, register_date TEXT, status TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS return_items (id INTEGER PRIMARY KEY AUTOINCREMENT, batch_id TEXT, barcode TEXT, return_type TEXT, expiry_date TEXT, quantity INTEGER, quality_status TEXT, damage_reason TEXT, operator TEXT, approval_status TEXT, created_at TEXT, remark TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS change_requests (req_id INTEGER PRIMARY KEY AUTOINCREMENT, item_id INTEGER, action TEXT, old_qty INTEGER, new_qty INTEGER, new_status TEXT, new_expiry TEXT, reason TEXT, status TEXT)")
    try: cursor.execute("ALTER TABLE change_requests ADD COLUMN new_expiry TEXT")
    except: pass
    try:
        cursor.execute("INSERT OR IGNORE INTO users (username, password, register_date, role, status) VALUES (?, ?, ?, ?, ?)", 
                       ("余宸緯", "123456", get_tw_now().strftime("%Y-%m-%d %H:%M:%S"), "管理者", "approved"))
    except:
        pass
    conn.commit(); conn.close()

init_db()

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
st.title("📦 物流退貨點收系統")

if not st.session_state['logged_in']:
    tab1, tab2 = st.tabs(["👤 帳號登入", "📝 新用戶註冊"])
    with tab1:
        login_name = st.text_input("請輸入中文真實姓名", key="login_name").strip()
        login_pwd = st.text_input("請輸入密碼", type="password", key="login_pwd")
        if st.button("進入系統"):
            conn = get_db_connection()
            user = conn.execute('SELECT * FROM users WHERE username = ?', (login_name,)).fetchone()
            if user:
                if user['password'] == login_pwd:
                    if login_name == ORIGINAL_ADMIN or user['status'] == 'approved':
                        st.session_state.update({'logged_in': True, 'username': login_name, 'is_admin': (user['role'] == "管理者" or login_name == ORIGINAL_ADMIN)})
                        st.rerun()
                    else: st.error("❌ 您的帳號尚未通過管理員審核，請稍候。")
                else: st.error("❌ 密碼錯誤，請重新輸入。")
            else: st.error("❌ 查無此帳號，請確認姓名或前往註冊。")
            conn.close()
    with tab2:
        reg_name = st.text_input("請輸入你的中文真實姓名", key="reg_name").strip()
        reg_pwd = st.text_input("自訂密碼", type="password", key="reg_pwd")
        if st.button("建立帳號"):
            conn = get_db_connection()
            try:
                role = "管理者" if reg_name == ORIGINAL_ADMIN else "一般用戶"
                status = "approved" if reg_name == ORIGINAL_ADMIN else "pending"
                conn.execute('INSERT INTO users (username, password, register_date, role, status) VALUES (?, ?, ?, ?, ?)', (reg_name, reg_pwd, get_tw_now().strftime("%Y-%m-%d %H:%M:%S"), role, status))
                conn.commit(); st.success("註冊成功！請等待管理者審核。")
            except: st.error("❌ 姓名已被註冊。")
            finally: conn.close()
else:
    st.sidebar.write(f"👤 作業員：**{st.session_state['username']}**")
    st.sidebar.write(f"👑 職位：**{'管理者' if st.session_state.get('is_admin') else '一般用戶'}**")
    if st.sidebar.button("登出系統"): st.session_state.clear(); st.rerun()
    
    conn = get_db_connection()
    pending_req_count = conn.execute("SELECT COUNT(*) FROM change_requests WHERE status = '審核中'").fetchone()[0]
    pending_user_count = conn.execute("SELECT COUNT(*) FROM users WHERE status = 'pending'").fetchone()[0]
    conn.close()

    tab_labels = ["📦 退貨點收作業", "🔍 歷史紀錄查詢與異常修正"]
    if st.session_state.get('is_admin'):
        review_label = f"🔔 主管審核工作台 ({pending_req_count})" if pending_req_count > 0 else "🔔 主管審核工作台"
        user_label = f"👥 員工權限維護 ({pending_user_count})" if pending_user_count > 0 else "👥 員工權限維護"
        tab_labels.extend([review_label, user_label])
    
    tabs = st.tabs(tab_labels)

    with tabs[0]:
        conn = get_db_connection()
        unfinished = conn.execute("SELECT batch_id, channel FROM return_batches WHERE status = '作業中'").fetchall()
        for b in unfinished:
            if not st.session_state.get('current_batch_id'):
                count = conn.execute("SELECT COUNT(*) FROM return_items WHERE batch_id = ?", (b['batch_id'],)).fetchone()[0]
                if st.button(f"繼續作業：:red[{b['batch_id']}] (:red[{b['channel']}]) | 已完成 {count} 筆"):
                    st.session_state.update({'current_batch_id': b['batch_id'], 'current_channel': b['channel']}); st.rerun()
        conn.close()

        if not st.session_state.get('current_batch_id'):
            st.divider()
            st.subheader("🚀 請設定本次作業環境與通路")
            env = st.radio("⚙️ 作業環境", ["正式環境", "測試環境"], horizontal=True) if st.session_state.get('is_admin') else "正式環境"
            chan = st.selectbox("🏬 選擇退貨通路", list(CHANNEL_CODES.keys()))
            if st.button("鎖定並開始作業"):
                prefix = "T-" if env == "測試環境" else ""
                code = CHANNEL_CODES[chan]
                today = get_tw_now().strftime("%Y%m%d")
                conn = get_db_connection()
                count = conn.execute("SELECT COUNT(*) FROM return_batches WHERE batch_id LIKE ?", (f"{prefix}{code}_{today}%",)).fetchone()[0]
                bid = f"{prefix}{code}_{today}_{count + 1:03d}"
                conn.execute("INSERT INTO return_batches VALUES (?, ?, ?, '作業中')", (bid, chan, today))
                conn.commit(); conn.close()
                st.session_state.update({'current_batch_id': bid, 'current_channel': chan}); st.rerun()
        else:
            st.info(f"🏬 通路：**{st.session_state.get('current_channel')}** ｜ 🧾 批號：**{st.session_state.get('current_batch_id')}**")
            b_input = st.text_input("🔍 請刷取商品條碼", key="barcode_field")
            r_type = st.radio("退貨形態", ["箱出", "散出", "組出"], horizontal=True)
            if r_type == "箱出":
                exp_date, qual, reason = "無效期", "良品", ""
            else:
                exp_date = st.text_input("有效期限 (格式:20260618)")
                qual = st.radio("商品貨況", ["良品", "不良品"], horizontal=True)
                reason = ", ".join(st.multiselect("不良原因", DAMAGE_REASONS)) if qual == "不良品" else ""
            qty = st.number_input("數量", min_value=1, step=1, value=1)
            remark = st.text_input("備註欄")
            
            if st.button("💾 儲存並繼續新增", use_container_width=True, type="primary"):
                # --- 新增條碼檢查邏輯 ---
                if b_input in BARCODE_ALERTS:
                    for alert in BARCODE_ALERTS[b_input]:
                        st.warning(f"⚠️ 條碼 {b_input} 提醒：{alert}")
                
                conn = get_db_connection()
                conn.execute("INSERT INTO return_items (batch_id, barcode, return_type, expiry_date, quantity, quality_status, damage_reason, operator, approval_status, created_at, remark) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (st.session_state['current_batch_id'], b_input, r_type, exp_date, qty, qual, reason, st.session_state['username'], '已確認', get_tw_now().strftime("%Y-%m-%d %H:%M:%S"), remark))
                count = conn.execute("SELECT COUNT(*) FROM return_items WHERE batch_id = ?", (st.session_state['current_batch_id'],)).fetchone()[0]
                conn.commit(); conn.close()
                st.session_state['last_count'] = count; st.session_state['show_success'] = True
            
            if st.session_state.get('show_success'):
                st.warning(f"✅ 儲存成功！目前本單已完成：{st.session_state.get('last_count')} 筆")
                if st.button("確認"): st.session_state['show_success'] = False; st.rerun()
            c1, c2 = st.columns(2)
            
            # 返回按鈕
            if c1.button("🔙 返回 / 暫停作業", use_container_width=True, key="back-btn"):
                st.session_state.update({'current_channel': "", 'current_batch_id': ""})
                st.rerun()
                
            # 關單按鈕
            if c2.button("🛑 結束 / 進行關單", use_container_width=True, key="close-btn"):
                conn = get_db_connection()
                conn.execute("UPDATE return_batches SET status = '已完成' WHERE batch_id = ?", (st.session_state['current_batch_id'],))
                conn.commit()
                conn.close()
                st.session_state.update({'current_channel': "", 'current_batch_id': ""})
                st.rerun()

with tabs[1]:
        st.header("🔍 歷史紀錄查詢與異常修正")
        with st.expander("⚙️ 篩選條件設定", expanded=True):
            if st.session_state.get('is_admin'):
                env_filter = st.radio("環境篩選", ["正式", "測試", "All"], horizontal=True)
            else:
                env_filter = "正式"
            
            # --- 篩選欄位 ---
            c1, c2 = st.columns(2)
            s_start = c1.date_input("開始日期", None)
            s_end = c2.date_input("結束日期", None)
            s_batch = st.text_input("單號 (批號)")
            c3, c4, c5 = st.columns(3)
            s_barcode = c3.text_input("商品條碼 (包含篩選)")
            s_operator = c4.text_input("作業員")
            s_type = c5.multiselect("形態", ["箱出", "散出", "組出"])
            
            if st.button("執行查詢"):
                conn = get_db_connection()
                query = "SELECT i.id, i.created_at, b.channel, i.batch_id, i.barcode, i.return_type, i.expiry_date, i.quantity, i.quality_status, i.damage_reason, i.operator FROM return_items i LEFT JOIN return_batches b ON i.batch_id = b.batch_id WHERE 1=1"
                params = []
                
                # 環境篩選邏輯
                if env_filter == "正式": query += " AND i.batch_id NOT LIKE 'T-%'"
                elif env_filter == "測試": query += " AND i.batch_id LIKE 'T-%'"
                
                if s_batch: query += " AND i.batch_id LIKE ?"; params.append(f"%{s_batch}%")
                if s_barcode: query += " AND i.barcode LIKE ?"; params.append(f"%{s_barcode}%")
                
                df = pd.read_sql_query(query, conn, params=params)
                df['ID'] = df['id']
                st.session_state['df'] = df
                conn.close()
        
        # 顯示結果與申請
        if 'df' in st.session_state and not st.session_state['df'].empty:
            edited_df = st.data_editor(st.session_state['df'], hide_index=True)
            selected = edited_df[edited_df.get("選取", False) == True]
            act = st.selectbox("動作", ["數量更正", "貨況更正", "效期更正", "刪除資料"])
            n_q = st.number_input("新數量", step=1) if act != "刪除資料" else 0
            if st.button("⚠️ 送出申請"):
                conn = get_db_connection()
                for _, row in selected.iterrows():
                    conn.execute("INSERT INTO change_requests (item_id, action, old_qty, new_qty, status) VALUES (?, ?, ?, ?, ?)", 
                                 (int(row['ID']), act, int(row['quantity']), int(n_q), "審核中"))
                conn.commit(); conn.close(); st.success("申請已送出")
        if st.session_state.get('is_admin'):
    with tabs[2]:
            st.header("🔔 主管審核工作台")
            conn = get_db_connection()
            # 查詢所有審核中的請求
            review_df = pd.read_sql_query("""
                SELECT c.*, i.batch_id, i.barcode, i.operator as applicant, i.expiry_date 
                FROM change_requests c 
                JOIN return_items i ON c.item_id = i.id 
                WHERE c.status = '審核中'
            """, conn)
            conn.close()
            
            if not review_df.empty:
                # 調整顯示名稱
                display = review_df[['batch_id', 'barcode', 'action', 'old_qty', 'new_qty', 'new_status', 'new_expiry', 'reason', 'applicant']]
                display.columns = ['單號', '商品條碼', '動作', '原數量', '新數量', '新狀態', '新效期', '原因', '申請人']
                display.insert(0, "同意", False)
                
                # 讓管理者進行批量勾選
                reviewed = st.data_editor(display, disabled=display.columns.drop("同意"), hide_index=True)
                
                if st.button("🟢 批量處理"):
                    conn = get_db_connection()
                    processed_count = 0
                    for i, row in reviewed.iterrows():
                        if row["同意"]:
                            req = review_df.iloc[i]
                            # 執行資料庫更新
                            if req['action'] == "刪除資料":
                                conn.execute("DELETE FROM return_items WHERE id = ?", (int(req['item_id']),))
                            elif req['action'] == "貨況更正":
                                conn.execute("UPDATE return_items SET quality_status = ? WHERE id = ?", (str(row['新狀態']), int(req['item_id'])))
                            elif req['action'] == "數量更正":
                                conn.execute("UPDATE return_items SET quantity = ? WHERE id = ?", (int(row['新數量']), int(req['item_id'])))
                            elif req['action'] == "效期更正":
                                conn.execute("UPDATE return_items SET expiry_date = ?, quantity = ? WHERE id = ?", (str(row['新效期']), int(row['新數量']), int(req['item_id'])))
                            
                            # 更新審核狀態
                            conn.execute("UPDATE change_requests SET status = '已確認' WHERE req_id = ?", (int(req['req_id']),))
                            processed_count += 1
                    
                    conn.commit()
                    conn.close()
                    if processed_count > 0:
                        st.success(f"✅ 已處理 {processed_count} 筆申請！")
                        st.rerun()
            else:
                # 這個提示只會出現在 tabs[2] 中
                st.info("✨ 目前沒有待審核的異常修正資料！")

        with tabs[3]:
            st.header("👥 員工權限")
            conn = get_db_connection()
            user_df = pd.read_sql_query("SELECT username as 名稱, register_date as 註冊日期時間, role as 用戶別, status as 狀態 FROM users", conn)
            conn.close()
            user_df.insert(0, "編號", range(1, len(user_df) + 1))
            st.dataframe(user_df, use_container_width=True, hide_index=True)
         
            
            t_u = st.text_input("輸入要操作的員工名稱").strip()
            c1, c2, c3, c4 = st.columns(4)
            if c1.button("✅ 審核通過"): 
                conn = get_db_connection(); conn.execute("UPDATE users SET status = 'approved' WHERE username = ?", (t_u,)); conn.commit(); conn.close(); st.rerun()
            if c2.button("🎖️ 調整為管理者"): 
                conn = get_db_connection(); conn.execute("UPDATE users SET role = '管理者' WHERE username = ?", (t_u,)); conn.commit(); conn.close(); st.rerun()
            if c3.button("👤 調整為一般用戶"): 
                conn = get_db_connection(); conn.execute("UPDATE users SET role = '一般用戶' WHERE username = ?", (t_u,)); conn.commit(); conn.close(); st.rerun()
            if c4.button("❌ 刪除（離職夥伴）"): 
                conn = get_db_connection(); conn.execute("DELETE FROM users WHERE username = ?", (t_u,)); conn.commit(); conn.close(); st.rerun()

























