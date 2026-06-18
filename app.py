import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

def get_tw_now():
    return datetime.utcnow() + timedelta(hours=8)

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
    cursor.execute("CREATE TABLE IF NOT EXISTS return_batches (batch_id TEXT PRIMARY KEY, channel TEXT, register_date TEXT, status TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS return_items (id INTEGER PRIMARY KEY AUTOINCREMENT, batch_id TEXT, barcode TEXT, return_type TEXT, expiry_date TEXT, quantity INTEGER, quality_status TEXT, damage_reason TEXT, operator TEXT, approval_status TEXT, created_at TEXT, remark TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS change_requests (req_id INTEGER PRIMARY KEY AUTOINCREMENT, item_id INTEGER, action TEXT, old_qty INTEGER, new_qty INTEGER, new_status TEXT, new_expiry TEXT, reason TEXT, status TEXT)")
    try: cursor.execute("ALTER TABLE change_requests ADD COLUMN new_expiry TEXT")
    except: pass
    conn.commit(); conn.close()

init_db()

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
st.title("📦 物流退貨點收系統")

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
    with tab2:
        reg_name = st.text_input("請輸入你的中文真實姓名", key="reg_name").strip()
        reg_pwd = st.text_input("自訂密碼", type="password", key="reg_pwd")
        if st.button("建立帳號"):
            conn = get_db_connection()
            try:
                conn.execute('INSERT INTO users VALUES (?, ?, ?, ?)', (reg_name, reg_pwd, get_tw_now().strftime("%Y-%m-%d %H:%M:%S"), "管理者" if reg_name == ORIGINAL_ADMIN else "一般用戶"))
                conn.commit(); st.success("註冊成功！")
            except: st.error("❌ 姓名已被註冊。")
            finally: conn.close()
else:
    st.sidebar.write(f"👤 作業員：**{st.session_state['username']}**")
    if st.sidebar.button("登出系統"): st.session_state.clear(); st.rerun()
    tabs = st.tabs(["📦 退貨點收作業", "🔍 歷史紀錄與更正", "🔔 主管審核工作台", "👥 員工權限維護"])

    with tabs[0]:
        # (您的點收邏輯保持不變)
        if not st.session_state.get('current_batch_id'):
            st.subheader("🚀 請設定本次作業環境與通路")
            conn = get_db_connection()
            unfinished = conn.execute("SELECT batch_id, channel FROM return_batches WHERE status = '作業中'").fetchall()
            for b in unfinished:
                count = conn.execute("SELECT COUNT(*) FROM return_items WHERE batch_id = ?", (b['batch_id'],)).fetchone()[0]
                if st.button(f"繼續作業：{b['batch_id']} ({b['channel']}) | 已完成 {count} 筆"): st.session_state.update({'current_batch_id': b['batch_id'], 'current_channel': b['channel']}); st.rerun()
            conn.close()
            env = st.radio("⚙️ 作業環境", ["正式環境", "測試環境"], horizontal=True) if st.session_state.get('is_admin') else "正式環境"
            chan = st.selectbox("🏬 選擇退貨通路", ["請選擇...", "MOMO", "寶雅", "康是美", "屈臣氏", "蝦皮", "家購", "大智通", "好市多","PCHPME","松本清","唐吉訶德"])
            if st.button("鎖定並開始作業"):
                prefix = "TEST" if env == "測試環境" else "Back"
                bid = prefix + get_tw_now().strftime("%Y%m%d") + "001"
                conn = get_db_connection(); conn.execute("INSERT INTO return_batches VALUES (?, ?, ?, '作業中')", (bid, chan, get_tw_now().strftime("%Y%m%d"))); conn.commit(); conn.close()
                st.session_state.update({'current_batch_id': bid, 'current_channel': chan}); st.rerun()
        else:
            st.info(f"批號：{st.session_state.get('current_batch_id')}")
            b_input = st.text_input("商品條碼"); r_type = st.radio("退貨形態", ["箱出", "散出", "組出"], horizontal=True)
            exp_date = st.text_input("有效期限"); qty = st.number_input("數量", min_value=1, step=1, value=1)
            qual = st.radio("商品貨況", ["良品", "不良品"], horizontal=True) if r_type != "箱出" else "良品"
            reason = ", ".join(st.multiselect("不良原因", DAMAGE_REASONS)) if qual == "不良品" else ""
            remark = st.text_input("備註欄")
            if st.button("💾 儲存並繼續新增", type="primary"):
                conn = get_db_connection()
                conn.execute("INSERT INTO return_items (batch_id, barcode, return_type, expiry_date, quantity, quality_status, damage_reason, operator, approval_status, created_at, remark) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (st.session_state['current_batch_id'], b_input, r_type, exp_date, qty, qual, reason, st.session_state['username'], '已確認', get_tw_now().strftime("%Y-%m-%d %H:%M:%S"), remark))
                conn.commit(); conn.close(); st.success("儲存成功")
            if st.button("🛑 結束作業"):
                conn = get_db_connection(); conn.execute("UPDATE return_batches SET status = '已完成' WHERE batch_id = ?", (st.session_state['current_batch_id'],)); conn.commit(); conn.close()
                st.session_state.update({'current_batch_id': ""}); st.rerun()

    with tabs[1]:
        st.header("🔍 歷史紀錄與更正")
        with st.expander("⚙️ 篩選條件設定", expanded=True):
            c1, c2 = st.columns(2); s_start = c1.date_input("開始日期", value=None); s_end = c2.date_input("結束日期", value=None)
            s_batch = st.text_input("退貨單號 (批號)")
            c3, c4, c5 = st.columns(3); s_barcode = c3.text_input("商品條碼"); s_operator = c4.text_input("作業員"); s_type = c5.multiselect("形態", ["箱出", "散出", "組出"])
            c6, c7 = st.columns(2); s_channel = c6.multiselect("通路", ["MOMO", "寶雅", "康是美", "屈臣氏", "蝦皮", "家購", "大智通", "好市多","PCHPME","松本清","唐吉訶德"]); s_quality = c7.multiselect("貨況", ["良品", "不良品"])
            if st.button("查詢數據"):
                conn = get_db_connection()
                df = pd.read_sql_query("SELECT id, batch_id, barcode, quantity, operator, quality_status, created_at FROM return_items WHERE batch_id LIKE ?", conn, params=(f"%{s_batch}%",))
                df.insert(0, "選取", False); st.session_state['df'] = df; conn.close()
        
        if 'df' in st.session_state and not st.session_state['df'].empty:
            edited_df = st.data_editor(st.session_state['df'], disabled=st.session_state['df'].columns.drop("選取"), hide_index=True)
            selected = edited_df[edited_df["選取"] == True]
            act = st.selectbox("選擇動作", ["更正數量", "貨況轉換", "效期更正", "刪除資料"])
            n_q = st.number_input("新數量", step=1)
            n_s = st.text_input("新貨況 (若為貨況轉換，不良品請標註原因)") if act == "貨況轉換" else ""
            n_e = st.text_input("新效期 (效期更正用)") if act == "效期更正" else ""
            
            if st.button("⚠️ 送出申請"):
                conn = get_db_connection()
                for _, row in selected.iterrows():
                    # 這裡使用 'id' 作為鍵值來讀取，修正 KeyError
                    conn.execute("INSERT INTO change_requests (item_id, action, old_qty, new_qty, new_status, new_expiry, reason, status) VALUES (?, ?, ?, ?, ?, ?, ?, '審核中')", 
                                 (int(row['id']), act, int(row['quantity']), int(n_q), n_s, n_e, act, "審核中"))
                conn.commit(); conn.close(); st.warning("申請已送出")

    with tabs[2]:
        st.header("🔔 主管審核工作台")
        conn = get_db_connection()
        query = "SELECT c.*, i.batch_id, i.barcode, i.operator as applicant FROM change_requests c JOIN return_items i ON c.item_id = i.id WHERE c.status = '審核中'"
        review_df = pd.read_sql_query(query, conn)
        conn.close()
        if not review_df.empty:
            display = review_df[['batch_id', 'barcode', 'action', 'old_qty', 'new_qty', 'new_status', 'new_expiry', 'applicant']]
            display.columns = ['單號', '商品條碼', '動作', '原數量', '新數量', '新狀態', '新效期', '申請人']
            display.insert(0, "同意", False)
            reviewed = st.data_editor(display, disabled=display.columns.drop("同意"), hide_index=True)
            if st.button("🟢 批量處理同意"):
                conn = get_db_connection()
                for i, row in reviewed.iterrows():
                    if row["同意"]:
                        req = review_df.iloc[i]
                        # 處理更正數量
                        if req['action'] == "更正數量": conn.execute("UPDATE return_items SET quantity = ? WHERE id = ?", (int(row['新數量']), int(req['item_id'])))
                        # 處理效期更正
                        elif req['action'] == "效期更正": conn.execute("UPDATE return_items SET expiry_date = ?, quantity = ? WHERE id = ?", (str(req['new_expiry']), int(row['新數量']), int(req['item_id'])))
                        # 處理貨況轉換
                        elif req['action'] == "貨況轉換":
                            conn.execute("UPDATE return_items SET quantity = quantity - ? WHERE id = ?", (int(row['新數量']), int(req['item_id'])))
                            item = conn.execute("SELECT * FROM return_items WHERE id = ?", (int(req['item_id']),)).fetchone()
                            conn.execute("INSERT INTO return_items (batch_id, barcode, return_type, quantity, quality_status, operator, approval_status, created_at) VALUES (?, ?, ?, ?, ?, ?, '已確認', ?)", (item['batch_id'], item['barcode'], item['return_type'], int(row['新數量']), str(req['new_status']), item['operator'], get_tw_now().strftime("%Y-%m-%d %H:%M:%S")))
                        conn.execute("UPDATE change_requests SET status = '已確認' WHERE req_id = ?", (int(req['req_id']),))
                conn.commit(); conn.close(); st.success("完成"); st.rerun()

    with tabs[3]:
        st.header("👥 員工權限")
        conn = get_db_connection(); st.dataframe(pd.read_sql_query("SELECT * FROM users", conn), use_container_width=True); conn.close()
        t_u = st.text_input("操作員工姓名").strip()
        c1, c2, c3 = st.columns(3)
        if c1.button("🎖️ 升職"): conn = get_db_connection(); conn.execute("UPDATE users SET role = '管理者' WHERE username = ?", (t_u,)); conn.commit(); conn.close(); st.rerun()
        if c2.button("👤 降職"): conn = get_db_connection(); conn.execute("UPDATE users SET role = '一般用戶' WHERE username = ?", (t_u,)); conn.commit(); conn.close(); st.rerun()
        if c3.button("❌ 刪除"): conn = get_db_connection(); conn.execute("DELETE FROM users WHERE username = ?", (t_u,)); conn.commit(); conn.close(); st.rerun()
