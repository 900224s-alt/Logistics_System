import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(layout="wide")

# 1. 資料庫連線 (使用絕對路徑以確保穩定)
def get_data(table_name):
    conn = sqlite3.connect('return_system.db')
    # 直接讀取整張表，完全不使用 WHERE 條件，避開 SQL 語法解析錯誤
    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    conn.close()
    return df

# 2. 登入與權限 (鎖定您的名稱)
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'username': "", 'is_admin': False})

if not st.session_state['logged_in']:
    name = st.text_input("姓名")
    if st.button("登入"):
        if name == "余宸緯":
            st.session_state.update({'logged_in': True, 'username': name, 'is_admin': True})
            st.rerun()
else:
    st.sidebar.write(f"👤 {st.session_state['username']}")
    tabs = st.tabs(["📦 點收", "🔍 歷史", "✅ 不良品簽核", "👥 人員管理"])

    with tabs[0]: # 點收
        bc = st.text_input("條碼")
        if st.button("儲存"):
            conn = sqlite3.connect('return_system.db')
            conn.execute('INSERT INTO return_items (barcode, quality_status, operator) VALUES (?,?,?)', 
                         (bc, "不良品", st.session_state['username']))
            conn.commit(); conn.close(); st.rerun()

    with tabs[1]: # 歷史
        df = get_data('return_items')
        # 在 Python 端篩選，而不是在 SQL 端篩選，確保不會報錯
        st.dataframe(df, use_container_width=True, hide_index=True)

    with tabs[2]: # 簽核 (手動篩選)
        if st.session_state['is_admin']:
            df = get_data('return_items')
            # 透過 Pandas 篩選出不良品與待簽核
            df_bad = df[(df['quality_status'] == '不良品') & (df['approved'] == '待簽核')]
            
            df_bad['簽核'] = False
            edited = st.data_editor(df_bad, hide_index=True, column_config={"簽核": st.column_config.CheckboxColumn()})
            
            if st.button("執行簽核"):
                conn = sqlite3.connect('return_system.db')
                for i, row in edited.iterrows():
                    if row['簽核']:
                        conn.execute("UPDATE return_items SET approved='已簽核' WHERE id=?", (int(row['id']),))
                conn.commit(); conn.close(); st.rerun()

    with tabs[3]: # 人員管理
        if st.session_state['is_admin']:
            df_users = get_data('users')
            st.dataframe(df_users, hide_index=True)
