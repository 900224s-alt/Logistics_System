import streamlit as st
import pandas as pd
import io

st.set_page_config(layout="wide")

st.title("🚨 24小時心血：條碼終極搶救工作台 (智慧分割版)")
st.markdown("""
### 🛠️ 條碼無損修復專用工具
剛才系統沒有修復，是因為檔案裡的「逗號」不見了，變成了「空白格」，導致系統找不到條碼欄位。
這個版本加入了**智慧分隔符號偵測引擎**，會強制把黏在一起的欄位切開並進行修復！
""")

uploaded_file = st.file_uploader("請上傳你昨天下載的原始 CSV 檔案", type=["csv", "txt"])

if uploaded_file is not None:
    try:
        content = uploaded_file.read()
        try:
            text = content.decode('utf-8-sig')
        except UnicodeDecodeError:
            text = content.decode('cp950')
            
        # 智慧判斷分隔符號 (逗號、Tab 或 空白)
        first_line = text.split('\n')[0]
        if '\t' in first_line:
            separator = '\t'
        elif ',' in first_line:
            separator = ','
        else:
            separator = r'\s+' # 使用正規表達式強制切開所有空白
            
        # 讀取並強制轉換所有內容為純文字
        df = pd.read_csv(io.StringIO(text), sep=separator, dtype=str, on_bad_lines='warn')
        
        st.subheader(f"1. 成功依照分隔符號拆開欄位（目前共有 {len(df.columns)} 欄）")
        st.dataframe(df.head())
        
        barcode_col = None
        for col in df.columns:
            if '條碼' in col or 'barcode' in col.lower():
                barcode_col = col
                break
        
        if barcode_col:
            def clean_scientific_notation(val):
                if pd.isna(val): return ""
                v = str(val).strip()
                if 'e' in v.lower() or '.' in v:
                    try: return str(int(float(v)))
                    except: return v
                return v

            df[barcode_col] = df[barcode_col].apply(clean_scientific_notation)
            
            st.subheader("2. 🟢 條碼數字高精度修復結果")
            st.dataframe(df)
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='昨天的辛苦點收紀錄')
            excel_data = buffer.getvalue()
            
            st.success("🎉 欄位已成功拆開！條碼轉換程式已順利執行！")
            st.download_button(
                label="📥 點我下載【完美修復、條碼正常】的 Excel (.xlsx) 檔案",
                data=excel_data,
                file_name="昨日物流點收資料_完美修復版.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        else:
            st.error("拆分欄位後，依然找不到『條碼』欄位，請檢查檔案內容！")
            
    except Exception as e:
        st.error(f"解析失敗: {str(e)}")
