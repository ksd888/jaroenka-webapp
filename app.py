import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
from google.oauth2 import service_account

# ตั้งค่า Credential
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"],
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
)

# เปิด Spreadsheet
gc = gspread.authorize(credentials)
spreadsheet = gc.open("สินค้าตู้เย็นปลีก_GS")
worksheet_main = spreadsheet.worksheet("ตู้เย็น")
worksheet_log = spreadsheet.worksheet("ยอดขาย")

# โหลดข้อมูลจากชีท "ตู้เย็น"
data = pd.DataFrame(worksheet_main.get_all_records())

st.title("📦 ระบบจัดการสินค้าตู้เย็น - เจริญค้า")

# คำนวณกำไรต่อหน่วย
data["กำไรต่อหน่วย"] = data["ราคาขาย"] - data["ต้นทุน"]

# ช่องค้นหา
search = st.text_input("🔍 ค้นหาชื่อสินค้า")
if search:
    data = data[data["ชื่อสินค้า"].str.contains(search, case=False)]

# แสดงตารางสินค้า
st.dataframe(data[["ชื่อสินค้า", "ราคาขาย", "ต้นทุน", "คงเหลือในตู้"]], use_container_width=True)

# เลือกสินค้า
selected = st.selectbox("เลือกสินค้า", data["ชื่อสินค้า"])

# ดึงข้อมูลสินค้า
row = data[data["ชื่อสินค้า"] == selected].index[0]

# ป้อนจำนวน
col1, col2 = st.columns(2)
with col1:
    qty_out = st.number_input("จำนวนที่ขายออก", min_value=0, step=1)
with col2:
    qty_in = st.number_input("จำนวนเติมสต๊อก", min_value=0, step=1)

# ปุ่มขาย
if st.button("🛒 ขายสินค้า"):
    data.at[row, "ออก"] += qty_out
    st.success(f"ขาย {selected} ออก {qty_out} หน่วย")

# ปุ่มเติม
if st.button("➕ เติมสต๊อก"):
    data.at[row, "เข้า"] += qty_in
    st.success(f"เติม {selected} เข้า {qty_in} หน่วย")

# ปุ่มแก้ไขจำนวนคงเหลือ
new_stock = st.number_input("แก้ไขจำนวนคงเหลือในตู้", value=int(data.at[row, "คงเหลือในตู้"]), step=1)
if st.button("✏️ แก้ไขจำนวน"):
    data.at[row, "คงเหลือในตู้"] = new_stock
    st.success("อัปเดตจำนวนคงเหลือแล้ว")

# คำนวณคงเหลือในตู้ใหม่
data["คงเหลือในตู้"] = data["คงเหลือในตู้"] + data["เข้า"] - data["ออก"]

# คำนวณกำไรรวม
data["กำไร"] = data["ออก"] * data["กำไรต่อหน่วย"]

# ปุ่มบันทึกยอดขายลง Google Sheet (ชีท "ยอดขาย")
if st.button("💾 บันทึกยอดขายวันนี้"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    summary_data = data[data["ออก"] > 0].copy()
    summary_data["วันที่"] = now
    summary_data["type"] = "drink"

    if not summary_data.empty:
        upload_df = summary_data[["วันที่", "ชื่อสินค้า", "ออก", "ราคาขาย", "ต้นทุน", "กำไร", "type"]]
        worksheet_log.append_rows(upload_df.values.tolist(), value_input_option="USER_ENTERED")
        st.success("บันทึกยอดขายเรียบร้อยแล้ว!")

# ปุ่มอัปเดตข้อมูลกลับไปชีทหลัก
if st.button("📤 อัปเดตกลับไป Google Sheet (ตู้เย็น)"):
    worksheet_main.update([data.columns.values.tolist()] + data.values.tolist())
    st.success("อัปเดตกลับชีทหลักสำเร็จ ✅"
