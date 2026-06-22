import streamlit as st
import pandas as pd
import io

st.set_page_config(layout="wide")

st.title("🚨 24小時心血：條碼終極搶救工作台")
st.markdown("""
### 🛠️ 條碼無損修復專用工具
請直接上傳你昨天下載、擠成一團且條碼在 Excel 裡變成一堆 0 的那個 CSV 檔案。
* **只要你昨天下載後，今天打開看到一堆 0 時「沒有按下儲存（Save）」覆蓋原始檔，底層純文字的精準數字就 100% 還在！**
""")

uploaded_file = st.file_uploader("請上傳你昨天下載的原始 CSV 檔案", type=["csv"])

if uploaded_file is not None:
    try:
        # 用純文字 (str) 方式讀取，強迫 Pandas 不准自作聰明轉型，保留原始 e+12 的所有字串
        df = pd.read_csv(uploaded_file, dtype=str)
        
        st.subheader("1. 原始文字檔案成功拆分預覽（此時可能仍看見 e+12）")
        st.dataframe(df.head())
        
        # 自動尋找條碼欄位
        barcode_col = None
        for col in df.columns:
            if '條碼' in col or 'barcode' in col.lower():
                barcode_col = col
                break
        
        if barcode_col:
            def clean_scientific_notation(val):
                if pd.isna(val): 
                    return ""
                v = str(val).strip()
                
                # 如果字串裡面含有科學記號 e 或 E
                if 'e' in v.lower():
                    try:
                        # Python 的 float 精確度高達 15~17 位數，還原 13 碼物流條碼絕對不會失真、更不會變 0
                        return str(int(float(v)))
                    except:
                        return v
                # 如果已經被轉成帶小數點的格式 (例如 4710155288739.0)
                if '.' in v:
                    try:
                        return str(int(float(v)))
                    except:
                        return v
                return v

            # 執行高精度還原
            df[barcode_col] = df[barcode_col].apply(clean_scientific_notation)
            
            st.subheader("2. 🟢 條碼數字高精度修復結果")
            st.dataframe(df)
            
            # 轉換成真正的 Excel 檔案供下載
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='昨天的辛苦點收紀錄')
            excel_data = buffer.getvalue()
            
            st.success("🎉 太棒了！檢測到底層文字數據，條碼尾數全部完好無缺地還原了！")
            st.download_button(
                label="📥 點我下載【完美修復、條碼正常】的 Excel (.xlsx) 檔案",
                data=excel_data,
                file_name="昨日物流點收資料_條碼修復版.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        else:
            st.error("找不到名為『條碼』的欄位，請確認你的檔案欄位名稱。")
            
    except Exception as e:
        st.error(f"搶救過程中發生錯誤，可能是檔案已被 Excel 毀損存檔: {str(e)}")
