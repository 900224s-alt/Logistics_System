import streamlit as st 
import sqlite3 
import pandas as pd 
from datetime import datetime, timedelta 

def get_tw_now(): 
    return datetime.utcnow() + timedelta(hours=8) 

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

# --- 登入邏輯 ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False 
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
else: 
    tabs = st.tabs(["📦 退貨點收作業", "🔍 歷史紀錄與更正", "🔔 主管審核工作台", "👥 員工權限維護"]) 
    
    with tabs[0]: 
        # (這裡放置您原先完整的點收作業邏輯)
        st.write("退貨點收作業區塊 (保持您原先的完整代碼即可)")

    with tabs[1]: 
        st.header("🔍 歷史紀錄與更正") 
        with st.expander("⚙️ 篩選條件設定", expanded=True): 
            c1, c2 = st.columns(2); s_start = c1.date_input("開始日期", value=None); s_end = c2.date_input("結束日期", value=None) 
            s_batch = st.text_input("退貨單號 (批號)") 
            c3, c4, c5 = st.columns(3); s_barcode = c3.text_input("商品條碼"); s_operator = c4.text_input("作業員"); s_type = c5.multiselect("形態", ["箱出", "散出", "組出"]) 
            c6, c7 = st.columns(2); s_channel = c6.multiselect("通路", ["MOMO", "寶雅", "康是美", "屈臣氏", "蝦皮", "家購", "大智通", "好市多","PCHPME","松本清","唐吉訶德"]); s_quality = c7.multiselect("貨況", ["良品", "不良品"]) 
            if st.button("查詢數據"): 
                conn = get_db_connection() 
                query = "SELECT i.*, b.channel FROM return_items i LEFT JOIN return_batches b ON i.batch_id = b.batch_id WHERE i.batch_id LIKE ?" 
                df = pd.read_sql_query(query, conn, params=(f"%{s_batch}%",)) 
                df['日期'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d') 
                df.insert(0, "選取", False) 
                df = df[['選取', '日期', 'channel', 'id', 'batch_id', 'barcode', 'return_type', 'expiry_date', 'quantity', 'quality_status', 'damage_reason', 'operator', 'approval_status', 'created_at']] 
                df.columns = ["選取", "日期", "通路", "ID", "退貨單號", "商品條碼", "箱散出", "效期", "數量", "良品不良品", "異常原因", "作業員", "訂單狀態", "時間"] 
                conn.close(); st.session_state['df'] = df
        if 'df' in st.session_state and not st.session_state['df'].empty: 
            edited_df = st.data_editor(st.session_state['df'], hide_index=True) 
            selected = edited_df[edited_df["選取"] == True] 
            st.subheader("🛠️ 異常修正操作區") 
            act = st.selectbox("選擇動作", ["更正數量", "貨況轉換", "效期更正", "刪除資料"]) 
            n_q = st.number_input("數值/數量", step=1); n_s = st.text_input("貨況/效期"); res = st.text_input("說明原因") 
            if st.button("⚠️ 送出更正申請"): 
                conn = get_db_connection() 
                for _, row in selected.iterrows(): 
                    conn.execute("INSERT INTO change_requests (item_id, action, old_qty, new_qty, new_status, new_expiry, reason, status) VALUES (?, ?, ?, ?, ?, ?, ?, '審核中')", (int(row['ID']), act, int(row['數量']), int(n_q), n_s if act == "貨況轉換" else "", n_e if act == "效期更正" else "", res)) 
                conn.commit(); conn.close(); st.warning("✅ 申請已送出") 

    with tabs[2]: 
        st.header("🔔 主管審核工作台") 
        conn = get_db_connection() 
        review_df = pd.read_sql_query("SELECT c.*, i.batch_id, i.barcode, i.created_at as apply_time, i.operator as applicant FROM change_requests c JOIN return_items i ON c.item_id = i.id WHERE c.status = '審核中'", conn) 
        conn.close() 
        if not review_df.empty: 
            display_df = review_df[['apply_time', 'batch_id', 'barcode', 'reason', 'old_qty', 'new_qty', 'applicant']] 
            display_df.columns = ['申請日期時間', '單號', '商品條碼', '修正原因', '修正前數量', '修正後數量', '申請人'] 
            display_df.insert(0, "同意", False) 
            reviewed_df = st.data_editor(display_df, hide_index=True) 
            if st.button("🟢 批量處理同意"): 
                conn = get_db_connection() 
                for i, row in reviewed_df.iterrows(): 
                    if row.get("同意"): 
                        req = review_df.iloc[i]
                        if req['action'] == "更正數量": conn.execute("UPDATE return_items SET quantity = ? WHERE id = ?", (int(row['修正後數量']), int(req['item_id']))) 
                        conn.execute("UPDATE change_requests SET status = '已確認' WHERE req_id = ?", (int(req['req_id']),)) 
                conn.commit(); conn.close(); st.rerun() 

    with tabs[3]: 
        st.header("👥 員工權限與離職維護") 
        conn = get_db_connection(); st.dataframe(pd.read_sql_query("SELECT * FROM users", conn), use_container_width=True); conn.close() 
        t_u = st.text_input("操作員工姓名").strip() 
        c1, c2, c3 = st.columns(3) 
        if c1.button("🎖️ 升職"): conn = get_db_connection(); conn.execute("UPDATE users SET role = '管理者' WHERE username = ?", (t_u,)); conn.commit(); conn.close(); st.rerun() 
        if c2.button("👤 降職"): conn = get_db_connection(); conn.execute("UPDATE users SET role = '一般用戶' WHERE username = ?", (t_u,)); conn.commit(); conn.close(); st.rerun() 
        if c3.button("❌ 刪除"): conn = get_db_connection(); conn.execute("DELETE FROM users WHERE username = ?", (t_u,)); conn.commit(); conn.close(); st.rerun()
