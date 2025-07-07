import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2 import service_account

# ตั้งค่าการเชื่อมต่อ Google Sheets
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"],
    scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
)
gc = gspread.authorize(credentials)
spreadsheet = gc.open("สินค้าตู้เย็นปลีก_GS")
sheet_main = spreadsheet.worksheet("ตู้เย็น")
sheet_sales = spreadsheet.worksheet("ยอดขาย")

# โหลดข้อมูลจากชีทหลัก
data = pd.DataFrame(sheet_main.get_all_records())

st.title("📦 ระบบจัดการสินค้าตู้เย็นเจริญค้า")

# แสดงตารางสินค้า
st.subheader("📋 รายการสินค้า")
st.dataframe(data)

# ปุ่มแก้ไขจำนวนสินค้า
st.subheader("✏️ แก้ไขจำนวนสินค้า")
edit_name = st.selectbox("เลือกสินค้าที่จะแก้ไข", data["ชื่อสินค้า"])
new_stock = st.number_input("จำนวนใหม่ที่ต้องการตั้งค่า", min_value=0, step=1)

if st.button("📌 อัปเดตจำนวน"):
    idx = data[data["ชื่อสินค้า"] == edit_name].index[0]
    data.at[idx, "คงเหลือในตู้"] = new_stock
    st.success(f"อัปเดตจำนวนสินค้าสำเร็จ: {edit_name} = {new_stock}")

# ปุ่มเติมสต๊อก
st.subheader("➕ เติมสินค้าเข้าตู้")
add_name = st.selectbox("เลือกสินค้าที่จะเติม", data["ชื่อสินค้า"], key="add")
add_qty = st.number_input("จำนวนที่ต้องการเติม", min_value=0, step=1, key="add_qty")

if st.button("✅ เติมสต๊อก"):
    idx = data[data["ชื่อสินค้า"] == add_name].index[0]
    data.at[idx, "เข้า"] += add_qty
    st.success(f"เติมสต๊อกสำเร็จ: {add_name} +{add_qty}")

# ปุ่มขายสินค้า
st.subheader("🛒 ขายสินค้า")
sell_name = st.selectbox("เลือกสินค้าที่จะขาย", data["ชื่อสินค้า"], key="sell")
sell_qty = st.number_input("จำนวนที่ขาย", min_value=0, step=1, key="sell_qty")

if st.button("💰 บันทึกการขาย"):
    idx = data[data["ชื่อสินค้า"] == sell_name].index[0]
    data.at[idx, "ออก"] += sell_qty
    st.success(f"ขายสินค้าเรียบร้อย: {sell_name} -{sell_qty}")

# คำนวณคงเหลือใหม่
data["คงเหลือในตู้"] = data["คงเหลือในตู้"] + data["เข้า"] - data["ออก"]

# คำนวณกำไรสุทธิ
data["กำไรต่อหน่วย"] = data["ราคาขาย"] - data["ต้นทุน"]
data["กำไร"] = data["ออก"] * data["กำไรต่อหน่วย"]

# สรุปยอดขาย
total_sales = (data["ออก"] * data["ราคาขาย"]).sum()
total_profit = data["กำไร"].sum()

st.subheader("📊 สรุปยอดขายวันนี้")
st.write(f"🧾 ยอดขายรวม: {total_sales:,.2f} บาท")
st.write(f"💸 กำไรรวม: {total_profit:,.2f} บาท")

# ปุ่มบันทึกยอดขายกลับไปยัง Google Sheet (ชีท: "ยอดขาย")
if st.button("📝 บันทึกยอดขายไปยังชีทยอดขาย"):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for _, row in data.iterrows():
        if row["ออก"] > 0:
            sheet_sales.append_row([
                now,
                row["ชื่อสินค้า"],
                int(row["ออก"]),
                float(row["ราคาขาย"]),
                float(row["ต้นทุน"]),
                float(row["กำไรต่อหน่วย"]),
                float(row["กำไร"])
            ])
    st.success("บันทึกยอดขายไปยังชีทยอดขายเรียบร้อย ✅")

# ปุ่มบันทึกกลับไปยังชีทหลัก
if st.button("💾 อัปเดตกลับชีทหลัก"):
    sheet_main.update([data.columns.values.tolist()] + data.values.tolist())
    st.success("อัปเดตกลับชีทหลักสำเร็จ ✅")
