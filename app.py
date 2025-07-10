
import streamlit as st
import pandas as pd
from google.oauth2 import service_account
import gspread
from datetime import datetime

# เชื่อมต่อ Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope
)
gc = gspread.authorize(credentials)
spreadsheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
worksheet = spreadsheet.worksheet("ตู้เย็น")

# โหลดข้อมูลจาก Google Sheet
data = worksheet.get_all_records()
df = pd.DataFrame(data)

# ✅ แก้ปัญหา KeyError และ TypeError
df.columns = df.columns.str.strip()  # ลบช่องว่าง
df["ราคาขาย"] = pd.to_numeric(df["ราคาขาย"], errors="coerce").fillna(0)
df["ต้นทุน"] = pd.to_numeric(df["ต้นทุน"], errors="coerce").fillna(0)
df["กำไรต่อหน่วย"] = df["ราคาขาย"] - df["ต้นทุน"]

# แสดงหน้าเว็บ
st.title("🧊 ร้านเจริญค้า - ระบบขายสินค้า")

search_term = st.text_input("🔍 ค้นหาสินค้า", "")
filtered_df = df[df["ชื่อสินค้า"].str.contains(search_term, case=False, na=False)] if search_term else df

# แสดงผลการค้นหา
for index, row in filtered_df.iterrows():
    st.markdown(f"**{row['ชื่อสินค้า']}**")
    st.write(f"ราคาขาย: {row['ราคาขาย']} บาท")
    st.write(f"กำไรต่อหน่วย: {row['กำไรต่อหน่วย']} บาท")

# แสดงตะกร้าสินค้า (mock-up)
st.subheader("🛒 ตะกร้าสินค้า")
st.write("ยังไม่มีรายการสินค้าในตะกร้า")
