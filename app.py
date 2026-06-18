import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- 莫蘭迪配色設定 ---
st.markdown("""
<style>
    div.stButton > button[kind="primary"] { background-color: #8da3b4 !important; border: none !important; color: white !important; }
    div.stButton > button#back-btn { background-color: #d4c4a8 !important; border: none !important; color: white !important; }
    div.stButton > button#close-btn { background-color: #c48b8b !important; border: none !important; color: white !important; }
</style>
""", unsafe_allow_html=True)

ORIGINAL_ADMIN = "余宸緯"
DAMAGE_REASONS = ["盒凹", "嚴重盒凹", "盒污", "畫痕", "已過期（一個月內）", "即期（兩個月內）", "短效（半年內）", "效期模糊", "批號模糊", "已開封", "已開封使用", "空盒", "膠膜破損", "膠膜嚴重破損", "膠膜污損", "色差", "漸層色差", "嚴重色差", "霧氣", "漏液", "嚴重漏液", "外盒有貼標籤", "外膜有貼標籤", "外膜有貼膠帶+盒內有貼標籤", "外盒有貼膠帶+盒內有貼標籤"]

def get_db_connection():
    conn = sqlite3.connect('return_system.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, register_date TEXT, role TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS return_batches (batch_id TEXT PRIMARY KEY, channel TEXT, register_date TEXT, status TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS return_items (id INTEGER PRIMARY KEY AUTOINCREMENT, batch_id TEXT, barcode TEXT, return_type TEXT, expiry_date TEXT, quantity INTEGER, quality_status TEXT, damage_reason TEXT, operator TEXT, approval_status TEXT, created_at TEXT, remark TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS change_requests (req_id INTEGER PRIMARY KEY AUTOINCREMENT, item_id INTEGER, action TEXT, old_qty INTEGER, new_qty INTEGER, new_status TEXT, reason TEXT, status TEXT)")
    conn.commit(); conn.close()

init_db()

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
st.title("📦 物流退貨點收系統")

if not st.session_state['logged_in']:
    tab1, tab2 = st.tabs(["👤 帳號登入", "📝 新人員註冊"])
    with tab1:
        login_name = st.text_input("姓名", key="l_n"); login_pwd = st.text_input("密碼", type="password", key="l_p")
        if st.button("登入"):
            conn = get_db_connection()
            user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (login_name, login_pwd)).fetchone()
            if user: st.session_state.update({'logged_in': True, 'username': login_name, 'is_admin': (user['role']=="管理者" or login_name==ORIGINAL_ADMIN)}); st.rerun()
            conn.close()
    with tab2:
        reg_name = st.text_input("姓名", key="r_n"); reg_pwd = st.text_input("密碼", type="password", key="r_p")
        if st.button("註冊"):
            conn = get_db_connection()
            try: conn.execute('INSERT INTO users VALUES (?, ?, ?, ?)', (reg_name, reg_pwd, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "一般用戶")); conn.commit(); st.success("OK")
            except: st.error("錯誤")
            conn.close()
else:
    tabs = st.tabs(["📦 退貨點收作業", "🔍 歷史紀錄與更正", "🔔 主管審核工作台", "👥 員工權限維護"])
    with tabs[0]:
        conn = get_db_connection()
        unfinished = conn.execute("SELECT batch_id, channel FROM return_batches WHERE status = '作業中'").fetchall()
        for b in unfinished:
            cnt = conn.execute("SELECT COUNT(*) FROM return_items WHERE batch_id = ?", (b['batch_id'],)).fetchone()[0]
            st.write(f"作業中單號：:red[{b['batch_id']}] | 通路：:red[{b['channel']}] | 已完成 {cnt} 筆")
        conn.close()
        
        if not st.session_state.get('cur_bid'):
            env = st.radio("環境", ["正式環境", "測試環境"], horizontal=True)
            chan = st.selectbox("通路", ["MOMO", "寶雅", "康是美", "屈臣氏", "蝦皮", "家購", "大智通", "好市多"])
            if st.button("鎖定並開始"):
                bid = f"{'TEST' if env == '測試環境' else 'Back'}{datetime.now().strftime('%Y%m%d%H%M%S')}"
                conn = get_db_connection(); conn.execute("INSERT INTO return_batches VALUES (?, ?, ?, '作業中')", (bid, chan, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))); conn.commit(); conn.close()
                st.session_state.update({'cur_bid': bid, 'cur_chan': chan}); st.rerun()
        else:
            b_input = st.text_input("條碼"); r_type = st.radio("形態", ["箱出", "散出", "組出"], horizontal=True)
            exp = st.text_input("效期"); qty = st.number_input("數量", 1); qual = st.radio("貨況", ["良品", "不良品"], horizontal=True)
            reason = ", ".join(st.multiselect("原因", DAMAGE_REASONS)) if qual == "不良品" else ""
            if st.button("儲存並繼續", type="primary"):
                conn = get_db_connection(); conn.execute('INSERT INTO return_items (batch_id, barcode, return_type, expiry_date, quantity, quality_status, damage_reason, operator, approval_status, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)', (st.session_state['cur_bid'], b_input, r_type, exp, qty, qual, reason, st.session_state['username'], '已確認', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))); conn.commit(); conn.close(); st.toast("✅")
            c1, c2 = st.columns(2)
            if c1.button("返回/暫停", key="back-btn"): st.session_state.pop('cur_bid'); st.rerun()
            if c2.button("關單", key="close-btn"): conn = get_db_connection(); conn.execute("UPDATE return_batches SET status = '已完成' WHERE batch_id = ?", (st.session_state['cur_bid'],)); conn.commit(); conn.close(); st.session_state.pop('cur_bid'); st.rerun()

    with tabs[1]:
        s_batch = st.text_input("查詢批號"); s_bar = st.text_input("商品條碼")
        if st.button("查詢數據"):
            conn = get_db_connection()
            query = "SELECT id, created_at, ' ' as 通路, batch_id, barcode, return_type, expiry_date, quantity, quality_status, damage_reason, operator, approval_status, remark, created_at as 時間 FROM return_items WHERE batch_id LIKE ? AND barcode LIKE ?"
            df = pd.read_sql_query(query, conn, params=(f"%{s_batch}%", f"%{s_bar}%"))
            df.columns = ["ID", "日期", "通路", "退貨單號", "商品條碼", "箱散出", "效期", "數量", "良品不良品", "異常原因", "作業員", "訂單狀態", "備註", "時間"]
            conn.close(); st.session_state['df'] = df
        if 'df' in st.session_state:
            df = st.session_state['df'].copy(); df.insert(0, "選取", False)
            edited = st.data_editor(df, hide_index=True)
            if st.button("送出更正"):
                conn = get_db_connection()
                for _, row in edited.iterrows():
                    if row.get('選取'): conn.execute("INSERT INTO change_requests (item_id, action, old_qty, new_qty, reason, status) VALUES (?, '更正數量', ?, 0, '申請', '審核中')", (row['ID'], row['數量']))
                conn.commit(); conn.close(); st.warning("已送出")
            st.download_button("下載CSV", df.to_csv(index=False), "data.csv")
    with tabs[2]: 
        st.header("🔔 主管審核工作台") 
        conn = get_db_connection(); review_df = pd.read_sql_query("SELECT * FROM change_requests WHERE status = '審核中'", conn); conn.close() 
        review_df.insert(0, "同意", False) 
        reviewed_df = st.data_editor(review_df, column_config={"同意": st.column_config.CheckboxColumn(required=True)}, hide_index=True) 
        if st.button("🟢 批量處理同意"): 
            conn = get_db_connection() 
            for _, row in reviewed_df.iterrows(): 
                if row.get("同意"): 
                    item = conn.execute("SELECT * FROM return_items WHERE id = ?", (row['item_id'],)).fetchone() 
                    if item:
                        if row['action'] == "刪除資料": conn.execute("DELETE FROM return_items WHERE id = ?", (row['item_id'],)) 
                        elif row['action'] == "更正數量": conn.execute("UPDATE return_items SET quantity = ? WHERE id = ?", (row['new_qty'], row['item_id'])) 
                        elif row['action'] == "貨況轉換": 
                            conn.execute("UPDATE return_items SET quantity = ? WHERE id = ?", (item['quantity'] - int(row['new_qty']), row['item_id'])) 
                            conn.execute("INSERT INTO return_items (batch_id, barcode, return_type, quantity, quality_status, damage_reason, approval_status, created_at) VALUES (?, ?, ?, ?, ?, ?, '已確認', ?)", (item['batch_id'], item['barcode'], item['return_type'], row['new_qty'], row['new_status'], row['reason'], datetime.now().strftime("%Y-%m-%d %H:%M:%S"))) 
                    conn.execute("UPDATE change_requests SET status = '已確認' WHERE req_id = ?", (row['req_id'],)) 
            conn.commit(); conn.close(); st.rerun() 

    with tabs[3]: 
        st.header("👥 員工權限與離職維護") 
        conn = get_db_connection(); st.dataframe(pd.read_sql_query("SELECT * FROM users", conn), use_container_width=True); conn.close() 
        t_u = st.text_input("操作員工姓名").strip() 
        c1, c2, c3 = st.columns(3) 
        if c1.button("🎖️ 升職"): conn = get_db_connection(); conn.execute("UPDATE users SET role = '管理者' WHERE username = ?", (t_u,)); conn.commit(); conn.close(); st.rerun() 
        if c2.button("👤 降職"): conn = get_db_connection(); conn.execute("UPDATE users SET role = '一般用戶' WHERE username = ?", (t_u,)); conn.commit(); conn.close(); st.rerun() 
        if c3.button("❌ 刪除"): conn = get_db_connection(); conn.execute("DELETE FROM users WHERE username = ?", (t_u,)); conn.commit(); conn.close(); st.rerun()
