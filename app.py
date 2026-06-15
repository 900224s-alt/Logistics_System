import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(layout="wide")

# 1. 設定檔案路徑 (自動產生此 CSV 檔)
DATA_FILE = 'logistics_data.csv'

def load_data():
    if not os.path.exists(DATA_FILE):
        return pd.DataFrame(columns=['id', 'barcode', 'quality_status', 'operator', 'approved'])
    return pd.read_csv(DATA_FILE)

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# 2. 登入邏輯
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'username': "", 'is_admin': False})

if not st.session_state['logged_in']:
    name = st.text_input("姓名")
    if st.button("登入"):
        # 強制指定您為管理者
        if name == "余宸緯":
            st.session_state.update({'logged_in': True, 'username': name, 'is_admin': True})
            st.rerun()
else:
    st.sidebar.write(f"👤 {st.session_state['username']}")
    tabs = st.tabs(["📦 點收", "🔍 歷史", "✅ 簽核", "👥 人員"])

    # A. 點收
    with tabs[0]:
        bc = st.text_input("條碼")
        if st.button("儲存"):
            df = load_data()
            new_id = len(df) + 1
            new_row = {'id': new_id, 'barcode': bc, 'quality_status': '不良品' if '不良' in bc else '良品', 'operator': st.session_state['username'], 'approved': '待簽核'}
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            save_data(df)
            st.success("儲存成功")

    # B. 歷史 (直接讀 CSV)
    with tabs[1]:
        df = load_data()
        st.dataframe(df, use_container_width=True, hide_index=True)

    # C. 簽核
    with tabs[2]:
        if st.session_state['is_admin']:
            df = load_data()
            mask = (df['quality_status'] == '不良品') & (df['approved'] == '待簽核')
            df_bad = df[mask].copy()
            df_bad['簽核'] = False
            edited = st.data_editor(df_bad, hide_index=True, column_config={"簽核": st.column_config.CheckboxColumn()})
            if st.button("執行簽核"):
                for i, row in edited.iterrows():
                    if row['簽核']:
                        df.loc[df['id'] == row['id'], 'approved'] = '已簽核'
                save_data(df)
                st.rerun()
        else: st.error("僅限管理員")

    # D. 人員管理
    with tabs[3]:
        st.write("已登入人員清單 (本系統為檔案式存儲)")
        st.dataframe(pd.DataFrame({'姓名': ['余宸緯'], '權限': ['管理者']}), hide_index=True)
