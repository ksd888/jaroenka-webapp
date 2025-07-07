import streamlit as st
import gspread
from google.oauth2 import service_account
import pandas as pd
from datetime import datetime

# โหลด Credentials จาก secrets
GCP_SERVICE_ACCOUNT = st.secrets["GCP_SERVICE_ACCOUNT"]
credentials = service_account.Credentials.from_service_account_info(GCP_SERVICE_ACCOUNT)
client = gspread.authorize(credentials)

# เปิด Google Sheet
SHEET_NAME = "สินค้าตู้เย็นปลีก_GS"
WORKSHEET_NAME = "ตู้เย็น"
sheet = client.open(SHEET_NAME).worksheet(WORKSHEET_NAME)
data = sheet.get_all_records()
df = pd.DataFrame(data)

# กำหนดชื่อคอลัมน์
df.columns = ['ชื่อสินค้า', 'ราคาขาย', 'ต้นทุน', 'กำไรต่อหน่วย', 'คงเหลือ', 'เข้า', 'ออก', 'คงเหลือในตู้', 'กำไร', 'สต๊อกสำรอง']

st.title("📦 ระบบจัดการสินค้าตู้เย็น - ร้านเจริญค้า")

# ระบบค้นหา
search = st.text_input("🔍 ค้นหาสินค้า", "")

# ฟังก์ชันอัปเดตข้อมูลกลับไปที่ Google Sheet
def update_sheet(df):
    sheet.update([df.columns.values.tolist()] + df.values.tolist())

# แสดงตารางสินค้า
filtered_df = df[df["ชื่อสินค้า"].str.contains(search, case=False, na=False)] if search else df.copy()

# ปุ่มขาย, เติม, แก้ไข
for i, row in filtered_df.iterrows():
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
    with col1:
        st.write(f"**{row['ชื่อสินค้า']}** (คงเหลือ: {row['คงเหลือ']}, ในตู้: {row['คงเหลือในตู้']})")
    with col2:
        if st.button("ขายสินค้า", key=f"sell_{i}"):
            df.at[i, "ออก"] += 1
            df.at[i, "คงเหลือในตู้"] -= 1
            df.at[i, "กำไร"] = df.at[i, "ออก"] * df.at[i, "กำไรต่อหน่วย"]
    with col3:
        if st.button("เติมสต๊อก", key=f"add_{i}"):
            df.at[i, "คงเหลือในตู้"] += 1
            df.at[i, "สต๊อกสำรอง"] -= 1
    with col4:
        if st.button("แก้ไขจำนวน", key=f"edit_{i}"):
            new_qty = st.number_input(f"🔧 ใส่จำนวนใหม่ของ {row['ชื่อสินค้า']}", value=int(row['คงเหลือ']), key=f"input_{i}")
            df.at[i, "คงเหลือ"] = new_qty

# คำนวณยอดรวม
total_sales = df["ออก"].sum()
total_profit = df["กำไร"].sum()
st.markdown(f"### 🧾 ยอดขายรวม: `{total_sales}` ชิ้น | 💰 กำไรสุทธิ: `{total_profit:.2f}` บาท")

# ปุ่มบันทึกยอดขาย
if st.button("📤 บันทึกยอดขายกลับไปที่ Google Sheet"):
    update_sheet(df)
    st.success("✅ บันทึกข้อมูลเรียบร้อยแล้ว!")
