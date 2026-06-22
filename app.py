import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
import pandas as pd
from datetime import datetime, timedelta

# 調整網頁版面，讓整體看起來更專業寬敞
st.set_page_config(layout="wide")

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

# --- 莫蘭迪配色與表格放大設定 ---
st.markdown("""
<style>
    div.stButton > button[kind="primary"] { background-color: #8da3b4 !important; border: none !important; color: white !important; }
    div.stButton > button#back-btn { background-color: #d4c4a8 !important; border: none !important; color: white !important; }
    div.stButton > button#close-btn { background-color: #c48b8b !important; border: none !important; color: white !important; }
    
    /* 表格樣式優化：讓上下左右的索引標題、內容、下拉選單全部變大且醒目 */
    [data-testid="stDataEditor"] *, [data-testid="stDataFrame"] * {
        font-size: 16px !important;
        font-weight: 500 !important;
    }
    .glide-data-grid {
        font-family: inherit !important;
    }
    div[data-testid="stSelectbox"] *, div[data-testid="stNumberInput"] * {
        font-size: 16px !important;
    }
</style>
""", unsafe_allow_html=True)

ORIGINAL_ADMIN = "余宸緯"
DAMAGE_REASONS = ["盒凹", "嚴重盒凹", "盒污", "劃痕", "防盜貼", "已過期（一個月內）", "即期（兩個月內）", "短效（半年內）", "效期模糊", "批號模糊", "已開封", "已開封使用", "空盒", "膠膜破損", "膠膜嚴重破損", "膠膜污損", "色差", "漸層色差", "嚴重色差", "霧氣", "漏液", "嚴重漏液", "外盒有貼標籤", "外膜有貼標籤", "外膜有貼膠帶+盒內有貼標籤", "外盒有貼膠帶+盒內有貼標籤"]

# --- 【高效優化】：使用 Streamlit 資源快取，建立永久連線池，徹底根除延遲卡頓 ---
@st.cache_resource
def init_connection_pool():
    # 建立一個常駐連線池，最多允許 10 個多執行緒同時共用這條高速公路
    pool = SimpleConnectionPool(
        minconn=1,
        maxconn=10,
        host="aws-1-ap-northeast-1.pooler.supabase.com",
        port="6543",
        user="postgres.zlmoazvoxadasdbdwbsl",
        password="ALS56606120",
        database="postgres",
        sslmode="require"
    )
    return pool

def get_db_connection():
    pool = init_connection_pool()
    return pool.getconn()

def release_db_connection(conn):
    pool = init_connection_pool()
    pool.putconn(conn)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY, 
            password TEXT, 
            register_date TEXT, 
            role TEXT,
            status TEXT DEFAULT 'pending'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS return_batches (
            batch_id TEXT PRIMARY KEY, 
            channel TEXT, 
            register_date TEXT, 
            status TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS return_items (
            id SERIAL PRIMARY KEY, 
            batch_id TEXT, 
            barcode TEXT, 
            return_type TEXT, 
            expiry_date TEXT, 
            quantity INTEGER, 
            quality_status TEXT, 
            damage_reason TEXT, 
            operator TEXT, 
            approval_status TEXT, 
            created_at TEXT, 
            remark TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS change_requests (
            req_id SERIAL PRIMARY KEY, 
            item_id INTEGER, 
            action TEXT, 
            old_qty INTEGER, 
            new_qty INTEGER, 
            new_status TEXT, 
            new_expiry TEXT, 
            reason TEXT, 
            status TEXT
        )
    """)
    
    cursor.execute("""
        INSERT INTO users (username, password, register_date, role, status) 
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (username) DO NOTHING
    """, ("余宸緯", "123456", get_tw_now().strftime("%Y-%m-%d %H:%M:%S"), "管理者", "approved"))
    
    conn.commit()
    cursor.close()
    release_db_connection(conn)

init_db()

# --- 瀏覽器 F5 重整防護 ---
if 'logged_in' not in st.session_state:
    if "user" in st.query_params and "role" in st.query_params:
        st.session_state['logged_in'] = True
        st.session_state['username'] = st.query_params["user"]
        st.session_state['is_admin'] = st.query_params["role"] == "admin"
    else:
        st.session_state['logged_in'] = False

st.title("📦 特捷物流退貨點收系統")

if not st.session_state['logged_in']:
    tab1, tab2 = st.tabs(["👤 帳號登入", "📝 新用戶註冊"])
    with tab1:
        login_name = st.text_input("請輸入中文真實姓名", key="login_name").strip()
        login_pwd = st.text_input("請輸入密碼", type="password", key="login_pwd")
        if st.button("進入系統"):
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute('SELECT * FROM users WHERE username = %s', (login_name,))
            user = cursor.fetchone()
            if user:
                if user['password'] == login_pwd:
                    if login_name == ORIGINAL_ADMIN or user['status'] == 'approved':
                        is_admin_user = (user['role'] == "管理者" or login_name == ORIGINAL_ADMIN)
                        st.session_state.update({'logged_in': True, 'username': login_name, 'is_admin': is_admin_user})
                        st.query_params["user"] = login_name
                        st.query_params["role"] = "admin" if is_admin_user else "user"
                        st.rerun()
                    else: st.error("❌ 您的帳號尚未通過管理員審核，請稍候。")
                else: st.error("❌ 密碼錯誤，請重新輸入。")
            else: st.error("❌ 查無此帳號，請確認姓名或前往註冊。")
            cursor.close()
            release_db_connection(conn)
    with tab2:
        reg_name = st.text_input("請輸入你的中文真實姓名", key="reg_name").strip()
        reg_pwd = st.text_input("自訂密碼", type="password", key="reg_pwd")
        if st.button("建立帳號"):
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                role = "管理者" if reg_name == ORIGINAL_ADMIN else "一般用戶"
                status = "approved" if reg_name == ORIGINAL_ADMIN else "pending"
                cursor.execute('INSERT INTO users (username, password, register_date, role, status) VALUES (%s, %s, %s, %s, %s)', (reg_name, reg_pwd, get_tw_now().strftime("%Y-%m-%d %H:%M:%S"), role, status))
                conn.commit()
                st.success("註冊成功！請等待管理者審核。")
            except: 
                st.error("❌ 姓名已被註冊。")
            finally: 
                cursor.close()
                release_db_connection(conn)
else:
    # --- 頂部右側局部刷新功能區 ---
    col_title, col_refresh = st.columns([9, 1])
    with col_refresh:
        if st.button("🔄 刷新數據", help="點擊此處原地更新資料庫數據，不影響目前頁面"):
            st.toast("數據已同步至最新狀態！")
            
    st.sidebar.write(f"👤 作業員：**{st.session_state['username']}**")
    st.sidebar.write(f"👑 職位：**{'管理者' if st.session_state.get('is_admin') else '一般用戶'}**")
    if st.sidebar.button("登出系統"): 
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM change_requests WHERE status = '審核中'")
    pending_req_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE status = 'pending'")
    pending_user_count = cursor.fetchone()[0]
    cursor.close()
    release_db_connection(conn)

    tab_labels = ["📦 退貨點收作業", "🔍 歷史紀錄查詢與異常修正"]
    if st.session_state.get('is_admin'):
        review_label = f"🔔 主管審核工作台 ({pending_req_count})" if pending_req_count > 0 else "🔔 主管審核工作台"
        user_label = f"👥 員工權限維護 ({pending_user_count})" if pending_user_count > 0 else "👥 員工權限維護"
        tab_labels.extend([review_label, user_label])
    
    tabs = st.tabs(tab_labels)

    with tabs[0]:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT batch_id, channel FROM return_batches WHERE status = '作業中'")
        unfinished = cursor.fetchall()
        for b in unfinished:
            if not st.session_state.get('current_batch_id'):
                cursor.execute("SELECT COUNT(*) FROM return_items WHERE batch_id = %s", (b['batch_id'],))
                count = cursor.fetchone()[0]
                if st.button(f"繼續作業：:red[{b['batch_id']}] (:red[{b['channel']}]) | 已完成 {count} 筆"):
                    st.session_state.update({'current_batch_id': b['batch_id'], 'current_channel': b['channel']})
                    st.rerun()
        cursor.close()
        release_db_connection(conn)

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
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM return_batches WHERE batch_id LIKE %s", (f"{prefix}{code}_{today}%",))
                count = cursor.fetchone()[0]
                bid = f"{prefix}{code}_{today}_{count + 1:03d}"
                cursor.close()
                release_db_connection(conn)
                
                st.session_state.update({
                    'current_batch_id': bid, 
                    'current_channel': chan,
                    'batch_created_in_db': False,
                    'today_date_str': today
                })
                st.rerun()
        else:
            st.info(f"🏬 通路：**{st.session_state.get('current_channel')}** ｜ 🧾 預計批號：**{st.session_state.get('current_batch_id')}**")
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
                if b_input in BARCODE_ALERTS:
                    for alert in BARCODE_ALERTS[b_input]:
                        st.warning(f"⚠️ 條碼 {b_input} 提醒：{alert}")
                
                conn = get_db_connection()
                cursor = conn.cursor()
                
                if not st.session_state.get('batch_created_in_db'):
                    cursor.execute("SELECT COUNT(*) FROM return_batches WHERE batch_id = %s", (st.session_state['current_batch_id'],))
                    check_exist = cursor.fetchone()[0]
                    if check_exist == 0:
                        cursor.execute("INSERT INTO return_batches VALUES (%s, %s, %s, '作業中')", 
                                     (st.session_state['current_batch_id'], st.session_state['current_channel'], st.session_state['today_date_str']))
                    st.session_state['batch_created_in_db'] = True
                
                cursor.execute("""
                    INSERT INTO return_items (batch_id, barcode, return_type, expiry_date, quantity, quality_status, damage_reason, operator, approval_status, created_at, remark) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
                """, (st.session_state['current_batch_id'], b_input, r_type, exp_date, qty, qual, reason, st.session_state['username'], '已確認', get_tw_now().strftime("%Y-%m-%d %H:%M:%S"), remark))
                
                new_item_id = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM return_items WHERE batch_id = %s", (st.session_state['current_batch_id'],))
                count = cursor.fetchone()[0]
                
                conn.commit()
                cursor.close()
                release_db_connection(conn)
                
                st.session_state['last_item_id'] = new_item_id
                st.session_state['last_count'] = count
                st.toast(f"🎉 儲存成功！雲端ID: {new_item_id}")
            
            if st.session_state.get('last_item_id'):
                st.success(f"✅ 上一筆儲存成功！該筆資料雲端 ID 為：:blue[**{st.session_state.get('last_item_id')}**] ｜ 目前本單已累積：{st.session_state.get('last_count')} 筆")
            
            st.divider()
            c1, c2 = st.columns(2)
            
            if c1.button("🔙 返回 / 暫停作業", use_container_width=True, key="back-btn"):
                st.session_state.update({'current_channel': "", 'current_batch_id': "", 'last_item_id': None, 'last_count': None})
                st.rerun()
                
            if c2.button("🛑 結束 / 進行關單", use_container_width=True, key="close-btn"):
                conn = get_db_connection()
                cursor = conn.cursor()
                if st.session_state.get('batch_created_in_db'):
                    cursor.execute("UPDATE return_batches SET status = '已完成' WHERE batch_id = %s", (st.session_state['current_batch_id'],))
                    conn.commit()
                cursor.close()
                release_db_connection(conn)
                st.session_state.update({'current_channel': "", 'current_batch_id': "", 'last_item_id': None, 'last_count': None})
                st.rerun()

    with tabs[1]:
        st.header("🔍 歷史紀錄查詢與異常修正")
        with st.expander("⚙️ 篩選條件設定", expanded=True):
            if st.session_state.get('is_admin'):
                env_filter = st.radio("環境篩選", ["正式", "測試", "All"], horizontal=True)
            else:
                env_filter = "正式"
            
            c1, c2 = st.columns(2)
            s_start = c1.date_input("開始日期", None)
            s_end = c2.date_input("結束日期", None)
            s_batch = st.text_input("單號 (批號)")
            c3, c4, c5 = st.columns(3)
            s_barcode = c3.text_input("商品條碼 (包含篩選)")
            s_operator = c4.text_input("作業員")
            s_type = c5.multiselect("形態", ["箱出", "散出", "組出"])
            c6, c7 = st.columns(2)
            s_channel = c6.multiselect("通路", list(CHANNEL_CODES.keys()))
            s_quality = c7.multiselect("貨況", ["良品", "不良品"])
            
            if st.button("執行查詢"):
                conn = get_db_connection()
                query = "SELECT i.id, i.created_at, b.channel, i.batch_id, i.barcode, i.return_type, i.expiry_date, i.quantity, i.quality_status, i.damage_reason, i.operator FROM return_items i LEFT JOIN return_batches b ON i.batch_id = b.batch_id WHERE 1=1"
                params = []
                
                if env_filter == "正式": 
                    query += " AND i.batch_id NOT LIKE 'T-%%'"
                elif env_filter == "測試": 
                    query += " AND i.batch_id LIKE 'T-%%'"
                
                if s_batch: 
                    query += " AND i.batch_id LIKE %s"; params.append(f"%{s_batch}%")
                if s_barcode: 
                    query += " AND i.barcode LIKE %s"; params.append(f"%{s_barcode}%")
                if s_operator: 
                    query += " AND i.operator LIKE %s"; params.append(f"%{s_operator}%")
                if s_type: 
                    query += " AND i.return_type IN %s"; params.append(tuple(s_type))
                
                df = pd.read_sql_query(query, conn, params=params)
                if not df.empty:
                    df['FullDate'] = pd.to_datetime(df['created_at'])
                    df['日期'] = df['FullDate'].dt.strftime('%Y-%m-%d')
                    df['時間'] = df['FullDate'].dt.strftime('%H:%M:%S')
                    df = df.rename(columns={'id': 'ID', 'channel': '通路', 'batch_id': '批號', 'barcode': '條碼', 'return_type': '形態', 'expiry_date': '效期', 'quantity': '數量', 'quality_status': '貨況', 'damage_reason': '原因', 'operator': '作業員'})
                    df = df[['日期', '通路', 'ID', '批號', '條碼', '形態', '效期', '數量', '貨況', '原因', '作業員', '時間']]
                    df.insert(0, "選取", False)
                    st.session_state['df'] = df
                else:
                    st.session_state['df'] = pd.DataFrame()
                    st.warning("查無符合條件的資料")
                # 釋放連線回連線池
                release_db_connection(conn)
        
        if 'df' in st.session_state and not st.session_state['df'].empty:
            all_cols = st.session_state['df'].columns
            disabled_cols = [c for c in all_cols if c != "選取"]
            
            edited_df = st.data_editor(st.session_state['df'], disabled=disabled_cols, hide_index=True)
            selected = edited_df[edited_df.get("選取", False) == True]
            
            csv_data = edited_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 下載目前查詢表格為 CSV",
                data=csv_data,
                file_name=f"退貨點收紀錄_{get_tw_now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                key="download_history_csv"
            )
            
            st.divider()
            act = st.selectbox("動作", ["數量更正", "貨況更正", "效期更正", "刪除資料"])
            n_q = st.number_input("新數量", step=1) if act != "刪除資料" else 0
            
            if st.button("⚠️ 送出申請"):
                conn = get_db_connection()
                cursor = conn.cursor()
                for _, row in selected.iterrows():
                    cursor.execute("INSERT INTO change_requests (item_id, action, old_qty, new_qty, status) VALUES (%s, %s, %s, %s, '審核中')", 
                                 (int(row['ID']), act, int(row['數量']), int(n_q)))
                conn.commit()
                cursor.close()
                release_db_connection(conn)
                st.success("申請已送出，待主管審核")

    # --- 主管審核 ---
    if st.session_state.get('is_admin'):
        with tabs[2]:
            st.header("🔔 主管審核工作台")
            review_container = st.container()
            with review_container:
                conn = get_db_connection()
                review_df = pd.read_sql_query("SELECT c.*, i.batch_id, i.barcode, i.operator as applicant, i.expiry_date FROM change_requests c JOIN return_items i ON c.item_id = i.id WHERE c.status = '審核中'", conn)
                release_db_connection(conn)
                
                if not review_df.empty:
                    display = review_df[['batch_id', 'barcode', 'action', 'old_qty', 'new_qty', 'reason', 'applicant']]
                    display.columns = ['單號', '商品條碼', '動作', '原數量', '新數量', '原因', '申請人']
                    display.insert(0, "同意", False)
                    
                    admin_disabled_cols = [c for c in display.columns if c != "同意"]
                    reviewed = st.data_editor(display, disabled=admin_disabled_cols, hide_index=True, key="admin_review_editor")
                    
                    review_csv = reviewed.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label="📥 下載待審核清單為 CSV",
                        data=review_csv,
                        file_name=f"待主管審核清單_{get_tw_now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        key="download_review_csv"
                    )
                    
                    if st.button("🟢 批量處理"):
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        processed_count = 0
                        for i, row in reviewed.iterrows():
                            if row["同意"]:
                                req = review_df.iloc[i]
                                if req['action'] == "刪除資料":
                                    cursor.execute("DELETE FROM return_items WHERE id = %s", (int(req['item_id']),))
                                elif req['action'] == "數量更正":
                                    cursor.execute("UPDATE return_items SET quantity = %s WHERE id = %s", (int(row['新數量']), int(req['item_id'])))
                                
                                cursor.execute("UPDATE change_requests SET status = '已確認' WHERE req_id = %s", (int(req['req_id']),))
                                processed_count += 1
                        conn.commit()
                        cursor.close()
                        release_db_connection(conn)
                        
                        if processed_count > 0:
                            st.success(f"✅ 審核完成，已成功處理 {processed_count} 筆申請！")
                            st.empty() 
                else:
                    st.info("✨ 目前沒有待審核的異常修正資料！")

        with tabs[3]:
            st.header("👥 員工權限")
            conn = get_db_connection()
            user_df = pd.read_sql_query("SELECT username as 名稱, register_date as 註冊日期時間, role as 用戶別, status as 狀態 FROM users", conn)
            release_db_connection(conn)
            user_df.insert(0, "編號", range(1, len(user_df) + 1))
            st.dataframe(user_df, use_container_width=True, hide_index=True)
            
            t_u = st.text_input("輸入要操作的員工名稱").strip()
            c1, c2, c3, c4 = st.columns(4)
            if c1.button("✅ 審核通過"): 
                conn = get_db_connection(); cursor = conn.cursor(); cursor.execute("UPDATE users SET status = 'approved' WHERE username = %s", (t_u,)); conn.commit(); cursor.close(); release_db_connection(conn); st.rerun()
            if c2.button("🎖️ 調整為管理者"): 
                conn = get_db_connection(); cursor = conn.cursor(); cursor.execute("UPDATE users SET role = '管理者' WHERE username = %s", (t_u,)); conn.commit(); cursor.close(); release_db_connection(conn); st.rerun()
            if c3.button("👤 調整為一般用戶"): 
                conn = get_db_connection(); cursor = conn.cursor(); cursor.execute("UPDATE users SET role = '一般用戶' WHERE username = %s", (t_u,)); conn.commit(); cursor.close(); release_db_connection(conn); st.rerun()
            if c4.button("❌ 刪除（離職夥伴）"): 
                conn = get_db_connection(); cursor = conn.cursor(); cursor.execute("DELETE FROM users WHERE username = %s", (t_u,)); conn.commit(); cursor.close(); release_db_connection(conn); st.rerun()
