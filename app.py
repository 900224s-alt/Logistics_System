import streamlit as st
import pandas as pd
import os

st.set_page_config(layout="wide")

# 鎖定路徑
DATA_FILE = "logistics_data.csv"

# 初始化 CSV
if not os.path.exists(DATA_FILE):
    pd.DataFrame(columns=['barcode', 'quality_status', 'operator', 'approved']).to_csv(DATA_FILE, index=False)

# 權限判定
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
    tabs = st.tabs(["📦 點收", "🔍 歷史", "✅ 簽核"])

    with tabs[0]: # 點收
        bc = st.text_input("條碼")
        if st.button("儲存"):
            df = pd.read_csv(DATA_FILE)
            new_row = pd.DataFrame([{'barcode': bc, 'quality_status': '不良品', 'operator': st.session_state['username'], 'approved': '待簽核'}])
            df = pd.concat([df, new_row], ignore_index=True)
            df.to_csv(DATA_FILE, index=False)
            st.success("儲存成功")

    with tabs[1]: # 歷史
        st.dataframe(pd.read_csv(DATA_FILE), use_container_width=True, hide_index=True)

    with tabs[2]: # 簽核
        if st.session_state['is_admin']:
            df = pd.read_csv(DATA_FILE)
            df['簽核'] = False
            edited = st.data_editor(df, hide_index=True, column_config={"簽核": st.column_config.CheckboxColumn()})
            if st.button("確認簽核"):
                edited.loc[edited['簽核'] == True, 'approved'] = '已簽核'
                edited.drop(columns=['簽核'], inplace=True)
                edited.to_csv(DATA_FILE, index=False)
                st.rerun()
