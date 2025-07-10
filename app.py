import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="ร้านเจริญค้า", layout="wide")

# เชื่อมต่อ Google Sheet
scope = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"],
    scopes=scope,
)
gc = gspread.authorize(credentials)
spreadsheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
sheet = spreadsheet.worksheet("ตู้เย็น")

# โหลดข้อมูลจาก Google Sheet
data = sheet.get_all_records()
df = pd.DataFrame(data)

# ฟังก์ชันแปลงเป็น float อย่างปลอดภัย
def safe_float(val):
    try:
        return float(val)
    except:
        return 0.0

# UI การค้นหา
search_term = st.text_input("ค้นหาชื่อสินค้า")
if "ชื่อสินค้า" in df.columns:
    filtered_df = df[df["ชื่อสินค้า"].astype(str).str.contains(search_term, case=False, na=False)]
else:
    st.error("ไม่พบคอลัมน์ 'ชื่อสินค้า' ในชีต Google Sheet")
    st.stop()

# แสดงผลลัพธ์สินค้า
for index, row in filtered_df.iterrows():
    st.markdown(f"### {row['ชื่อสินค้า']}")
    st.write(f"ราคาขาย: {safe_float(row['ราคาขาย'])} บาท")
    st.write(f"คงเหลือ: {safe_float(row['คงเหลือ'])} ชิ้น")
    st.write("---")

