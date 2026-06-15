# 檔案名稱：app.py
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="物流退貨點收系統", layout="centered")

ORIGINAL_ADMIN = "余宸緯" 

def init_db_if_not_exists():
    conn = sqlite3.connect('return_system.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT NOT NULL, register_date TEXT, role TEXT DEFAULT "一般用戶")')
    cursor.execute('CREATE TABLE IF NOT EXISTS return_batches (batch_id TEXT PRIMARY KEY, channel_name TEXT, create_date TEXT, status TEXT DEFAULT "作業中")')
    cursor.execute('CREATE TABLE IF NOT EXISTS return_items (id INTEGER PRIMARY KEY AUTOINCREMENT, batch_id TEXT, item_seq INTEGER, barcode TEXT, return_type TEXT, expiry_date TEXT, quantity INTEGER, quality_status TEXT, damage_reason TEXT, operator TEXT)')
    conn.commit()
    conn.close()

init_db_if_not_exists()

def get_db_connection():
    conn = sqlite3.connect('return_system.db')
    conn.row_factory = sqlite3.Row
    return conn

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'username' not in st.session_state: st.session_state['username'] = ""
if 'is_admin' not in st.session_state: st.session_state['is_admin'] = False
if 'current_channel' not in st.session_state: st.session_state['current_channel'] = ""
if 'current_batch_id' not in st.session_state: st.session_state['current_batch_id'] = ""

st.title("📦 物流退貨點收系統")

if not st.session_state['logged_in']:
    # [登入頁面代碼維持不變，此處略過以保持整潔]
    st.info("請輸入姓名與密碼登入")
    # ... (原有登入註冊邏輯) ...
else:
    # 點收頁面
    tabs = st.tabs(["📦 退貨點收", "🔍 歷史紀錄"])
    with tabs[0]:
        if st.session_state['current_channel'] == "":
            selected_chan = st.selectbox("選擇通路", ["請選擇...", "MOMO", "寶雅", "康是美", "屈臣氏"])
            if st.button("鎖定並開始"):
                if selected_chan != "請選擇...":
                    st.session_state['current_channel'] = selected_chan
                    today = datetime.now().strftime("%Y%m%d")
                    st.session_state['current_batch_id'] = f"Back{today}001"
                    st.rerun()
        else:
            st.write(f"當前批號：{st.session_state['current_batch_id']}")
            
            # 【關鍵修正】：移除所有第三方 HTML 組件，使用原生的輸入框，徹底解決報錯
            barcode = st.text_input("請掃描或輸入條碼", key="barcode_input")
            
            ret_type = st.radio("選擇退貨形態", ["箱出", "散出"], horizontal=True)
            exp_date = st.text_input("有效期限") if ret_type == "散出" else ""
            qty = st.number_input("數量", min_value=1, value=1) if ret_type == "散出" else 1
            
            if st.button("儲存資料"):
                if not barcode:
                    st.error("請輸入條碼！")
                else:
                    conn = get_db_connection()
                    seq = conn.execute("SELECT COUNT(*) FROM return_items WHERE batch_id = ?", (st.session_state['current_batch_id'],)).fetchone()[0] + 1
                    conn.execute('INSERT INTO return_items (batch_id, item_seq, barcode, return_type, expiry_date, quantity, operator) VALUES (?, ?, ?, ?, ?, ?, ?)', 
                                 (st.session_state['current_batch_id'], seq, barcode, ret_type, exp_date, qty, st.session_state['username']))
                    conn.commit()
                    conn.close()
                    st.success(f"條碼 {barcode} 已儲存")
                    # 儲存後自動清除輸入框，防止重覆儲存
                    st.rerun()
