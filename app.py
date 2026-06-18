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

# (init_db, login, sidebar 邏輯與前一版本相同，為節省篇幅直接接續核心頁面)

    with tabs[1]:
        st.header("🔍 歷史紀錄與更正")
        with st.expander("⚙️ 篩選條件設定", expanded=True):
            c1, c2 = st.columns(2); s_start = c1.date_input("開始日期", None); s_end = c2.date_input("結束日期", None)
            s_batch = st.text_input("單號 (批號)")
            c3, c4, c5 = st.columns(3); s_barcode = c3.text_input("商品條碼"); s_operator = c4.text_input("作業員"); s_type = c5.multiselect("形態", ["箱出", "散出", "組出"])
            c6, c7 = st.columns(2); s_channel = c6.multiselect("通路", ["MOMO", "寶雅", "康是美", "屈臣氏", "蝦皮", "家購", "大智通", "好市多","PCHPME","松本清","唐吉訶德"]); s_quality = c7.multiselect("貨況", ["良品", "不良品"])
            
            if st.button("查詢數據"):
                conn = get_db_connection()
                # 包含篩選邏輯的 SQL
                query = """SELECT i.id, i.created_at, b.channel, i.batch_id, i.barcode, i.return_type, i.expiry_date, i.quantity, i.quality_status, i.damage_reason, i.operator 
                           FROM return_items i LEFT JOIN return_batches b ON i.batch_id = b.batch_id 
                           WHERE i.batch_id LIKE ?"""
                df = pd.read_sql_query(query, conn, params=(f"%{s_batch}%",))
                
                # 處理日期與時間分開
                df['FullDate'] = pd.to_datetime(df['created_at'])
                df['日期'] = df['FullDate'].dt.strftime('%Y-%m-%d')
                df['時間'] = df['FullDate'].dt.strftime('%H:%M:%S')
                
                # 重新命名欄位順序
                df = df.rename(columns={'id': 'ID', 'batch_id': '批號', 'barcode': '條碼', 'return_type': '形態', 'expiry_date': '效期', 'quantity': '數量', 'quality_status': '貨況', 'damage_reason': '原因', 'operator': '作業員'})
                df = df[['日期', 'channel', 'ID', '批號', '條碼', '形態', '效期', '數量', '貨況', '原因', '作業員', '時間']]
                df = df.rename(columns={'channel': '通路'})
                
                df.insert(0, "選取", False)
                st.session_state['df'] = df; conn.close()
        
        if 'df' in st.session_state and not st.session_state['df'].empty:
            edited_df = st.data_editor(st.session_state['df'], disabled=st.session_state['df'].columns.drop("選取"), hide_index=True)
            selected = edited_df[edited_df["選取"] == True]
            act = st.selectbox("動作", ["更正數量", "貨況轉換", "效期更正", "刪除資料"])
            n_q = st.number_input("新數量", step=1)
            n_s = st.radio("新貨況", ["良品", "不良品"], horizontal=True) if act == "貨況轉換" else ""
            n_reason = ", ".join(st.multiselect("不良原因", DAMAGE_REASONS)) if act == "貨況轉換" and n_s == "不良品" else ""
            n_e = st.text_input("新效期") if act == "效期更正" else ""
            if st.button("⚠️ 送出申請"):
                conn = get_db_connection()
                for _, row in selected.iterrows():
                    conn.execute("INSERT INTO change_requests (item_id, action, old_qty, new_qty, new_status, new_expiry, reason, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                                 (int(row['ID']), act, int(row['數量']), int(n_q), n_s, n_e, n_reason if n_reason else act, "審核中"))
                conn.commit(); conn.close(); st.warning("申請已送出")
    with tabs[2]:
        st.header("🔔 主管審核工作台")
        conn = get_db_connection()
        query = "SELECT c.*, i.batch_id, i.barcode, i.operator as applicant FROM change_requests c JOIN return_items i ON c.item_id = i.id WHERE c.status = '審核中'"
        review_df = pd.read_sql_query(query, conn)
        conn.close()
        if not review_df.empty:
            display = review_df[['batch_id', 'barcode', 'action', 'old_qty', 'new_qty', 'new_status', 'new_expiry', 'reason', 'applicant']]
            display.columns = ['單號', '商品條碼', '動作', '原數量', '新數量', '新狀態', '新效期', '原因', '申請人']
            display.insert(0, "同意", False)
            reviewed = st.data_editor(display, disabled=display.columns.drop("同意"), hide_index=True)
            if st.button("🟢 批量處理"):
                conn = get_db_connection()
                for i, row in reviewed.iterrows():
                    if row["同意"]:
                        req = review_df.iloc[i]
                        if req['action'] == "更正數量": conn.execute("UPDATE return_items SET quantity = ? WHERE id = ?", (int(row['新數量']), int(req['item_id'])))
                        elif req['action'] == "效期更正": conn.execute("UPDATE return_items SET expiry_date = ?, quantity = ? WHERE id = ?", (str(req['new_expiry']), int(row['新數量']), int(req['item_id'])))
                        elif req['action'] == "貨況轉換":
                            conn.execute("UPDATE return_items SET quantity = quantity - ? WHERE id = ?", (int(row['新數量']), int(req['item_id'])))
                            item = conn.execute("SELECT * FROM return_items WHERE id = ?", (int(req['item_id']),)).fetchone()
                            conn.execute("INSERT INTO return_items (batch_id, barcode, return_type, quantity, quality_status, damage_reason, operator, approval_status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, '已確認', ?)", (item['batch_id'], item['barcode'], item['return_type'], int(row['新數量']), str(req['new_status']), str(req['reason']), item['operator'], get_tw_now().strftime("%Y-%m-%d %H:%M:%S")))
                        conn.execute("UPDATE change_requests SET status = '已確認' WHERE req_id = ?", (int(req['req_id']),))
                conn.commit(); conn.close(); st.rerun()

    with tabs[3]:
        st.header("👥 員工權限")
        conn = get_db_connection(); st.dataframe(pd.read_sql_query("SELECT * FROM users", conn), use_container_width=True); conn.close()
        t_u = st.text_input("操作姓名").strip()
        c1, c2, c3 = st.columns(3)
        if c1.button("🎖️ 升職"): conn = get_db_connection(); conn.execute("UPDATE users SET role = '管理者' WHERE username = ?", (t_u,)); conn.commit(); conn.close(); st.rerun()
        if c2.button("👤 降職"): conn = get_db_connection(); conn.execute("UPDATE users SET role = '一般用戶' WHERE username = ?", (t_u,)); conn.commit(); conn.close(); st.rerun()
        if c3.button("❌ 刪除"): conn = get_db_connection(); conn.execute("DELETE FROM users WHERE username = ?", (t_u,)); conn.commit(); conn.close(); st.rerun()
