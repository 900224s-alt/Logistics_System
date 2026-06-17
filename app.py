import streamlit as st  
import sqlite3  
import pandas as pd  
from datetime import datetime  

st.set_page_config(page_title="物流退貨點收系統", layout="centered")  

ORIGINAL_ADMIN = "余宸緯"   

DAMAGE_REASONS = [  
    "盒凹", "嚴重盒凹", "盒污", "劃痕", "已過期（一個月內）", "即期（兩個月內）", "短效（半年內）",  
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
    cursor.execute("CREATE TABLE IF NOT EXISTS return_items (id INTEGER PRIMARY KEY AUTOINCREMENT, batch_id TEXT, barcode TEXT, return_type TEXT, expiry_date TEXT, quantity INTEGER, quality_status TEXT, damage_reason TEXT, operator TEXT, approval_status TEXT, created_at TEXT)")
    cursor.execute("PRAGMA table_info(return_batches)")
    if 'status' not in [row[1] for row in cursor.fetchall()]:
        conn.execute("ALTER TABLE return_batches ADD COLUMN status TEXT")
    conn.commit(); conn.close()  

init_db()  

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False  
if 'username' not in st.session_state: st.session_state['username'] = ""  
if 'current_channel' not in st.session_state: st.session_state['current_channel'] = ""  
if 'current_batch_id' not in st.session_state: st.session_state['current_batch_id'] = ""  

@st.dialog("💾 儲存成功")
def show_save_success(count):
    st.success("此筆條碼已成功建立！")
    st.info(f"本批次目前已累計完成筆數：**{count} 筆**")
    if st.button("確認"): st.rerun()

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
            else: st.error("❌ 姓名或密碼錯誤。")  
    with tab2:  
        reg_name = st.text_input("請輸入你的中文真實姓名", key="reg_name").strip()  
        reg_pwd = st.text_input("自訂密碼", type="password", key="reg_pwd")  
        if st.button("建立帳號", use_container_width=True):  
            conn = get_db_connection()  
            try:  
                role = "管理者" if reg_name == ORIGINAL_ADMIN else "一般用戶"  
                conn.execute('INSERT INTO users VALUES (?, ?, ?, ?)', (reg_name, reg_pwd, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), role))  
                conn.commit(); st.success("註冊成功！")  
            except: st.error("❌ 姓名已被註冊。")  
            finally: conn.close()  
else:  
    st.sidebar.write(f"👤 作業員：**{st.session_state['username']}**")  
    if st.sidebar.button("登出系統"): st.session_state.clear(); st.rerun()  

    tabs = st.tabs(["📦 退貨點收作業", "🔍 歷史紀錄與修改申請", "🔔 主管修改批核", "👥 員工權限與離職維護"])  
    
    with tabs[0]:  
        if st.session_state['current_channel'] == "":  
            st.subheader("🚀 請設定本次作業環境與通路")  
            conn = get_db_connection()
            unfinished = conn.execute("SELECT batch_id, channel FROM return_batches WHERE status = '作業中'").fetchall()
            if unfinished:
                st.warning("⚠️ 發現有未完成的單，請選擇繼續：")
                for b in unfinished:
                    if st.button(f"繼續作業：{b['batch_id']} ({b['channel']})"):
                        st.session_state.update({'current_batch_id': b['batch_id'], 'current_channel': b['channel']})
                        st.rerun()
            conn.close()
            
            env = st.radio("⚙️ 作業環境", ["正式環境", "測試環境"], horizontal=True) if st.session_state.get('is_admin') else "正式環境"  
            chan = st.selectbox("🏬 選擇退貨通路", ["請選擇...", "MOMO", "寶雅", "康是美", "屈臣氏", "蝦皮", "家購", "大智通", "好市多","PCHPME","松本清","唐吉訶德"])  
            if st.button("鎖定並開始作業", use_container_width=True):  
                if chan != "請選擇...":  
                    today = datetime.now().strftime("%Y%m%d")  
                    prefix = "TEST" if env == "測試環境" else "Back"  
                    conn = get_db_connection()  
                    count = conn.execute("SELECT COUNT(*) FROM return_batches WHERE batch_id LIKE ?", (f"{prefix}{today}%",)).fetchone()[0]  
                    bid = f"{prefix}{today}{count + 1:03d}"
                    conn.execute("INSERT INTO return_batches VALUES (?, ?, ?, '作業中')", (bid, chan, today))  
                    conn.commit(); conn.close()  
                    st.session_state.update({'current_batch_id': bid, 'current_channel': chan})  
                    st.rerun()  
        else:  
            st.info(f"🏬 通路：**{st.session_state['current_channel']}** ｜ 🧾 批號：**{st.session_state['current_batch_id']}**")  
            b_input = st.text_input("🔍 請刷取商品條碼", key="barcode_field")  
            
            if b_input:
                st.success(f"📥 目前帶入條碼：**{b_input}**")
                if b_input in ["4710155288739", "4710155287558"]: st.warning("⚠️ 提醒：勿拆成單品單件")
                if b_input in ["4710155284779", "4710155285837", "4710155281877", "4710155274527"]: st.warning("⚠️ 提醒：請額外裝箱並貼上大字報（好壞品分開放）")
                if b_input in ["4710155282249", "4710155277528", "4710155279522", "4710155277573", "4710155282188", "4710155285653", "4710155285912", "4710155278921", "4710155282386", "4710155278860"]: st.warning("⚠️ 提醒：需退回工廠商品，請額外裝箱並貼上大字報（好壞品分開放）")

            r_type = st.radio("選擇退貨形態", ["箱出", "散出"], horizontal=True)  
            qual = st.radio("商品貨況", ["良品", "不良品"], horizontal=True)
            reason = ", ".join(st.multiselect("勾選不良品原因", DAMAGE_REASONS)) if qual == "不良品" else ""
            
            if st.button("💾 儲存並繼續新增", use_container_width=True, type="primary"):  
                conn = get_db_connection()  
                status = '審核中' if qual == '不良品' else '已確認'
                conn.execute('INSERT INTO return_items (batch_id, barcode, return_type, quantity, quality_status, damage_reason, operator, approval_status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', 
                             (st.session_state['current_batch_id'], b_input, r_type, 1, qual, reason, st.session_state['username'], status, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))  
                count = conn.execute("SELECT COUNT(*) FROM return_items WHERE batch_id = ?", (st.session_state['current_batch_id'],)).fetchone()[0]
                conn.commit(); conn.close()
                if qual == "不良品": st.error("⚠️ 已送出異常申請，待主管簽核，請先和主管回報異常。")
                show_save_success(count)

            c1, c2 = st.columns(2)
            if c1.button("🛑 結束作業並關單"):
                conn = get_db_connection()
                conn.execute("UPDATE return_batches SET status = '已完成' WHERE batch_id = ?", (st.session_state['current_batch_id'],))
                conn.commit(); conn.close()
                st.session_state.update({'current_channel': "", 'current_batch_id': ""}); st.rerun()
            if c2.button("🔙 返回/暫停作業"):
                st.session_state.update({'current_channel': "", 'current_batch_id': ""}); st.rerun()

    with tabs[1]:
        st.header("🔍 歷史紀錄與更正")
        s_batch = st.text_input("輸入批號篩選")
        if st.button("查詢"):
            conn = get_db_connection()
            df = pd.read_sql_query("SELECT * FROM return_items WHERE batch_id LIKE ?", conn, params=(f"%{s_batch}%",))
            conn.close(); st.dataframe(df, use_container_width=True)

    with tabs[2]:
        st.header("🔔 主管審核工作台")
        conn = get_db_connection()
        review_df = pd.read_sql_query("SELECT * FROM return_items WHERE approval_status IN ('審核中', '申請刪除')", conn)
        conn.close()
        st.dataframe(review_df, use_container_width=True)
        app_id = st.number_input("輸入處理 ID", min_value=1, step=1)
        if st.button("🟢 同意變更"):
            conn = get_db_connection(); conn.execute("UPDATE return_items SET approval_status = '已確認' WHERE id = ?", (app_id,)); conn.commit(); conn.close(); st.rerun()

    with tabs[3]:
        st.header("👥 員工權限與離職維護")
        conn = get_db_connection()
        users_df = pd.read_sql_query("SELECT username AS 中文姓名, register_date AS 註冊日期, role AS 目前身分 FROM users", conn)
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
