import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timezone, timedelta

# --- 台灣時間處理 ---
TW = timezone(timedelta(hours=8))

# --- 莫蘭迪配色設定 ---
st.markdown("""
<style>
    div.stButton > button[kind="primary"] { background-color: #8da3b4 !important; border: none !important; color: white !important; }
    div.stButton > button#back-btn { background-color: #d4c4a8 !important; border: none !important; color: white !important; }
    div.stButton > button#close-btn { background-color: #c48b8b !important; border: none !important; color: white !important; }
</style>
""", unsafe_allow_html=True)

ORIGINAL_ADMIN = "余宸緯"
DAMAGE_REASONS = [
    "盒凹", "嚴重盒凹", "盒污", "畫痕", "已過期（一個月內）", "即期（兩個月內）", "短效（半年內）",
    "效期模糊", "批號模糊", "已開封", "已開封使用", "空盒", "膠膜破損", "膠膜嚴重破損", "膠膜污損",
    "色差", "漸層色差", "嚴重色差", "霧氣", "漏液", "嚴重漏液", "外盒有貼標籤", "外膜有貼標籤",
    "外膜有貼膠帶+盒內有貼標籤", "外盒有貼膠帶+盒內有貼標籤"
]

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
    cursor.execute("CREATE TABLE IF NOT EXISTS change_requests (req_id INTEGER PRIMARY KEY AUTOINCREMENT, item_id INTEGER, action TEXT, old_qty INTEGER, new_qty INTEGER, new_status TEXT, reason TEXT, status TEXT)")
    conn.commit(); conn.close()

init_db()

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'username' not in st.session_state: st.session_state['username'] = ""

st.title("📦 物流退貨點收系統")

if not st.session_state['logged_in']:
    tab1, tab2 = st.tabs(["👤 帳號登入", "📝 新人員註冊"])
    with tab1:
        login_name = st.text_input("請輸入中文真實姓名", key="login_name").strip()
        login_pwd = st.text_input("請輸入密碼", type="password", key="login_pwd")
        if st.button("進入系統", use_container_width=True):
            conn = get_db_connection()
            user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (login_name, login_pwd)).fetchone()
            conn.close()
            if user:
                st.session_state.update({'logged_in': True, 'username': login_name, 'is_admin': (user['role'] == "管理者" or login_name == ORIGINAL_ADMIN)})
                st.rerun()
    with tab2:
        reg_name = st.text_input("請輸入你的中文真實姓名", key="reg_name").strip()
        reg_pwd = st.text_input("自訂密碼", type="password", key="reg_pwd")
        if st.button("建立帳號", use_container_width=True):
            conn = get_db_connection()
            try:
                role = "管理者" if reg_name == ORIGINAL_ADMIN else "一般用戶"
                conn.execute('INSERT INTO users VALUES (?, ?, ?, ?)', (reg_name, reg_pwd, datetime.now(TW).strftime("%Y-%m-%d %H:%M:%S"), role))
                conn.commit(); st.success("註冊成功！")
            except: st.error("❌ 姓名已被註冊。")
            finally: conn.close()
else:
    st.sidebar.write(f"👤 作業員：**{st.session_state['username']}**")
    if st.sidebar.button("登出系統"): st.session_state.clear(); st.rerun()
    tabs = st.tabs(["📦 退貨點收作業", "🔍 歷史紀錄與更正", "🔔 主管審核工作台", "👥 員工權限維護"])

    with tabs[0]:
        if not st.session_state.get('current_channel'):
            st.subheader("🚀 請設定本次作業環境與通路")
            conn = get_db_connection()
            unfinished = conn.execute("SELECT batch_id, channel FROM return_batches WHERE status = '作業中'").fetchall()
            for b in unfinished:
                count = conn.execute("SELECT COUNT(*) FROM return_items WHERE batch_id = ?", (b['batch_id'],)).fetchone()[0]
                if st.button(f"繼續作業：:red[{b['batch_id']}] (:red[{b['channel']}]) | 已完成 {count} 筆"):
                    st.session_state.update({'current_batch_id': b['batch_id'], 'current_channel': b['channel']}); st.rerun()
            conn.close()
            chan = st.selectbox("🏬 選擇退貨通路", ["請選擇...", "MOMO", "寶雅", "康是美", "屈臣氏", "蝦皮", "家購", "大智通", "好市多","PCHPME","松本清","唐吉訶德"])
            if st.button("鎖定並開始作業", use_container_width=True):
                if chan != "請選擇...":
                    today = datetime.now(TW).strftime("%Y%m%d")
                    conn = get_db_connection()
                    count = conn.execute("SELECT COUNT(*) FROM return_batches WHERE batch_id LIKE ?", (f"Back{today}%",)).fetchone()[0]
                    bid = f"Back{today}{count + 1:03d}"
                    conn.execute("INSERT INTO return_batches VALUES (?, ?, ?, '作業中')", (bid, chan, today))
                    conn.commit(); conn.close()
                    st.session_state.update({'current_batch_id': bid, 'current_channel': chan}); st.rerun()
        else:
            st.info(f"🏬 通路：**{st.session_state.get('current_channel')}** ｜ 🧾 批號：**{st.session_state.get('current_batch_id')}**")
            b_input = st.text_input("🔍 請刷取商品條碼", key="barcode_field")
            r_type = st.radio("選擇退貨形態", ["箱出", "散出", "組出"], horizontal=True)
            exp_date = st.text_input("有效期限 (格式:20260618 或填入：無效期)")
            qty = st.number_input("輸入數量", min_value=1, step=1, value=1)
            qual = st.radio("商品貨況", ["良品", "不良品"], horizontal=True)
            reason = ", ".join(st.multiselect("勾選不良品原因", DAMAGE_REASONS)) if qual == "不良品" else ""
            remark = st.text_input("備註欄")

            if st.button("💾 儲存並繼續新增", use_container_width=True, type="primary"):
                conn = get_db_connection()
                conn.execute('''INSERT INTO return_items (batch_id, barcode, return_type, expiry_date, quantity, quality_status, damage_reason, operator, approval_status, created_at, remark) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                             (st.session_state['current_batch_id'], b_input, r_type, exp_date, qty, qual, reason, st.session_state['username'], '已確認', datetime.now(TW).strftime("%Y-%m-%d %H:%M:%S"), remark))
                conn.commit(); conn.close(); st.toast("✅ 儲存成功！")
            
            c1, c2 = st.columns(2)
            if c1.button("🔙 返回 / 暫停作業", use_container_width=True, key="back-btn"): st.session_state.update({'current_channel': "", 'current_batch_id': ""}); st.rerun()
            if c2.button("🛑 結束作業並關單", use_container_width=True, key="close-btn"): 
                conn = get_db_connection(); conn.execute("UPDATE return_batches SET status = '已完成' WHERE batch_id = ?", (st.session_state['current_batch_id'],)); conn.commit(); conn.close()
                st.session_state.update({'current_channel': "", 'current_batch_id': ""}); st.rerun()

    with tabs[1]:
        st.header("🔍 歷史紀錄與更正")
        s_batch = st.text_input("退貨單號 (批號)")
        if st.button("查詢數據"):
            conn = get_db_connection()
            df = pd.read_sql_query("SELECT * FROM return_items WHERE batch_id LIKE ?", conn, params=(f"%{s_batch}%",))
            # 補回時間欄位至最右側
            df['日期與時間'] = df['created_at']
            conn.close(); st.session_state['df'] = df

        if 'df' in st.session_state and not st.session_state['df'].empty:
            df = st.session_state['df'].copy()
            df.insert(0, "選取", False)
            edited_df = st.data_editor(df, hide_index=True)
            selected = edited_df[edited_df["選取"] == True]
            act = st.selectbox("選擇動作", ["更正數量", "貨況轉換", "刪除資料"])
            n_q = st.number_input("新數值", step=1); res = st.text_input("說明原因")
            
            if st.button("⚠️ 送出更正申請"):
                conn = get_db_connection()
                for _, row in selected.iterrows():
                    # 改為依賴選取狀態，不再強制依賴 id 欄位邏輯錯誤導致崩潰
                    conn.execute("INSERT INTO change_requests (item_id, action, old_qty, new_qty, reason, status) VALUES (?, ?, ?, ?, ?, '審核中')", 
                                 (row.get('id', 0), act, row.get('quantity', 0), str(n_q), res))
                conn.commit(); conn.close(); st.warning("✅ 申請已送出")

    with tabs[2]:
        st.header("🔔 主管審核工作台")
        conn = get_db_connection(); review_df = pd.read_sql_query("SELECT * FROM change_requests WHERE status = '審核中'", conn); conn.close()
        review_df.insert(0, "同意", False)
        reviewed_df = st.data_editor(review_df, hide_index=True)
        if st.button("🟢 批量處理同意"):
            conn = get_db_connection()
            for _, row in reviewed_df.iterrows():
                if row.get("同意"):
                    if row['action'] == "刪除資料": conn.execute("DELETE FROM return_items WHERE id = ?", (row['item_id'],))
                    elif row['action'] == "更正數量": conn.execute("UPDATE return_items SET quantity = ? WHERE id = ?", (row['new_qty'], row['item_id']))
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
