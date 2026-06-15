# app.py
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from io import BytesIO

st.set_page_config(page_title="物流退貨點收系統", layout="centered")

ORIGINAL_ADMIN = "余宸緯"

def init_db_if_not_exists():
    conn = sqlite3.connect('return_system.db')
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT NOT NULL,
        register_date TEXT,
        role TEXT DEFAULT '一般用戶'
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS return_batches (
        batch_id TEXT PRIMARY KEY,
        channel_name TEXT,
        create_date TEXT,
        status TEXT DEFAULT '作業中'
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS return_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        create_date TEXT,
        batch_id TEXT,
        item_seq INTEGER,
        barcode TEXT,
        return_type TEXT,
        expiry_date TEXT,
        quantity INTEGER,
        quality_status TEXT,
        damage_reason TEXT,
        operator TEXT
    )
    """)

    conn.commit()
    conn.close()

def upgrade_database():
    conn = sqlite3.connect('return_system.db')
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(return_items)")
    cols = [c[1] for c in cursor.fetchall()]

    if "create_date" not in cols:
        cursor.execute("ALTER TABLE return_items ADD COLUMN create_date TEXT")

    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect('return_system.db')
    conn.row_factory = sqlite3.Row
    return conn

def export_excel(df):
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        export_df = df.copy()
        export_df["barcode"] = export_df["barcode"].astype(str)

        export_df.to_excel(writer, index=False, sheet_name="退貨紀錄")

        ws = writer.sheets["退貨紀錄"]

        for cell in ws["D"]:
            cell.number_format = "@"

    return output.getvalue()

init_db_if_not_exists()
upgrade_database()

for k,v in {
    "logged_in":False,
    "username":"",
    "is_admin":False,
    "current_channel":"",
    "current_batch_id":"",
    "current_env":"正式環境",
    "saving":False
}.items():
    if k not in st.session_state:
        st.session_state[k]=v

st.title("📦 物流退貨點收系統")

if not st.session_state["logged_in"]:
    st.info("請將你原本登入註冊區塊貼回來（此檔已保留資料庫與報表修正）")
else:

    tabs = st.tabs(["📦退貨點收作業","🔍歷史紀錄"])

    with tabs[0]:
        barcode = st.text_input("商品條碼")
        ret_type = st.radio("退貨型態",["箱出","散出"])

        if st.button(
            "💾 儲存並繼續新增",
            disabled=st.session_state["saving"]
        ):

            st.session_state["saving"] = True

            conn = get_db_connection()

            seq = conn.execute(
                "SELECT COUNT(*) FROM return_items"
            ).fetchone()[0] + 1

            conn.execute("""
            INSERT INTO return_items
            (
            create_date,
            batch_id,
            item_seq,
            barcode,
            return_type,
            expiry_date,
            quantity,
            quality_status,
            damage_reason,
            operator
            )
            VALUES
            (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                datetime.now().strftime("%Y/%m/%d"),
                "TEST",
                seq,
                str(barcode).strip(),
                ret_type,
                "",
                1,
                "良品",
                "",
                st.session_state["username"]
            ))

            conn.commit()
            conn.close()

            st.session_state["saving"] = False
            st.toast(f"第 {seq} 筆儲存成功")

    with tabs[1]:

        conn = get_db_connection()

        col1,col2,col3 = st.columns(3)

        with col1:
            search_date = st.text_input("建檔日期")

        with col2:
            search_barcode = st.text_input("商品條碼")

        with col3:
            search_operator = st.text_input("Operator")

        query = "SELECT * FROM return_items WHERE 1=1"
        params = []

        if search_date:
            query += " AND create_date = ?"
            params.append(search_date)

        if search_barcode:
            query += " AND barcode LIKE ?"
            params.append(f"%{search_barcode}%")

        if search_operator:
            query += " AND operator LIKE ?"
            params.append(f"%{search_operator}%")

        query += " ORDER BY id DESC"

        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        st.metric("查詢結果筆數", len(df))

        if not df.empty:
            st.dataframe(df, use_container_width=True)

            excel_data = export_excel(df)

            st.download_button(
                "📥 匯出Excel",
                data=excel_data,
                file_name=f"退貨紀錄_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
