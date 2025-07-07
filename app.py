import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

# ตั้งค่าการเข้าถึง Google Sheet
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("speedy-aurora-464900-h3.json", scope)
client = gspread.authorize(creds)

# ดึงข้อมูลจาก Google Sheet
sheet = client.open("สินค้าตู้เย็นปลีก_GS").worksheet("ตู้เย็น")
data = sheet.get_all_records()
df = pd.DataFrame(data)

# UI หน้าจอ Streamlit
st.title("ระบบจัดการสินค้าตู้เย็น (เจริญค้า) 🧊")

search = st.text_input("🔍 ค้นหาชื่อสินค้า")
if search:
    df = df[df["ชื่อสินค้า"].str.contains(search, case=False, na=False)]

st.dataframe(df)

# ปุ่มอัปเดตยอดขาย (ตัวอย่างเบื้องต้น)
if st.button("📤 บันทึกยอดขายตัวอย่าง"):
    sheet.append_row(["เครื่องดื่มตัวอย่าง", 12, 8, 4, 5, 2, 1, 6, 4])  # ใส่ข้อมูลตัวอย่าง
    st.success("บันทึกข้อมูลสำเร็จ ✅")
