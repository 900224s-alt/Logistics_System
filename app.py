import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import pytz

# 設定台灣時區
TAIWAN_TZ = pytz.timezone('Asia/Taipei')

def get_now_str():
    return datetime.now(TAIWAN_TZ).strftime("%Y-%m-%d %H:%M:%S")

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
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, register_date TEXT, role TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS return_batches (batch_id TEXT PRIMARY KEY, channel TEXT, register_date TEXT, status TEXT)")
    # 確保包含 expiry_date
    cursor.execute("CREATE TABLE IF NOT EXISTS return_items (id INTEGER PRIMARY KEY AUTOINCREMENT, batch_id TEXT, barcode TEXT, return_type TEXT, expiry_date TEXT, quantity INTEGER, quality_status TEXT, damage_reason TEXT, operator TEXT, approval_status TEXT, created_at TEXT, remark TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS change_requests (req_id INTEGER PRIMARY KEY AUTOINCREMENT, item_id INTEGER, action TEXT, old_qty INTEGER, new_qty INTEGER, new_status TEXT, reason TEXT, status TEXT)")
    conn.commit(); conn.close()

init_db()

# [登入與 Session 處理邏輯保持原樣...]
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'username' not in st.session_state: st.session_state['username'] = ""

st.title("📦 物流退貨點收系統")

if not st.session_state['logged_in']:
    # ... (登入邏輯不變)
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
                conn.execute('INSERT INTO users VALUES (?, ?, ?, ?)', (reg_name, reg_pwd, get_now_str(), role))
                conn.commit(); st.success("註冊成功！")
            except: st.error("❌ 姓名已被註冊。")
            finally: conn.close()
else:
    # ... (作業區塊)
    tabs = st.tabs(["📦 退貨點收作業", "🔍 歷史紀錄與更正", "🔔 主管審核工作台", "👥 員工權限維護"])
    with tabs[0]:
        # ... (儲存邏輯改用 get_now_str())
        if st.button("💾 儲存並繼續新增", use_container_width=True, type="primary"):
            conn = get_db_connection()
            conn.execute('''INSERT INTO return_items 
                            (batch_id, barcode, return_type, expiry_date, quantity, quality_status, damage_reason, operator, approval_status, created_at, remark) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                            (st.session_state['current_batch_id'], b_input, r_type, exp_date, qty, qual, reason, st.session_state['username'], '已確認', get_now_str(), remark))
            conn.commit(); conn.close(); st.toast("✅ 儲存成功！")

    with tabs[1]:
        st.header("🔍 歷史紀錄與更正")
        if st.button("查詢數據"):
            conn = get_db_connection()
            df = pd.read_sql_query("SELECT * FROM return_items", conn) # 直接讀取所有欄位
            conn.close(); st.session_state['df'] = df
        
        if 'df' in st.session_state and not st.session_state['df'].empty:
            df = st.session_state['df']
            df.insert(0, "選取", False)
            edited_df = st.data_editor(df, hide_index=True)
            selected = edited_df[edited_df["選取"] == True]
            
            if st.button("⚠️ 送出更正申請"):
                conn = get_db_connection()
                for _, row in selected.iterrows():
                    # 修正這裡的 KeyError：確保直接從 row 讀取 DataFrame 的列名
                    conn.execute("INSERT INTO change_requests (item_id, action, old_qty, new_qty, new_status, reason, status) VALUES (?, ?, ?, ?, ?, ?, '審核中')", 
                                 (row['id'], act, row['quantity'], str(n_q), n_s, res))
                conn.commit(); conn.close(); st.warning("✅ 申請已送出")

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
