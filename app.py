import streamlit as st
import gspread
import pandas as pd
import json
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# โหลด GCP credentials จาก secrets (ผ่านหน้าเว็บหรือ .streamlit/secrets.toml)
service_account_info = json.loads(st.secrets["GCP_SERVICE_ACCOUNT"])
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)

# อ่านข้อมูลจาก Google Sheet
sheet = client.open("สินค้าตู้เย็นปลีก_GS").worksheet("ตู้เย็น")
data = sheet.get_all_records()
df = pd.DataFrame(data)

# ทำความสะอาดชื่อคอลัมน์
df.columns = df.columns.str.strip()

# ตั้งค่าตัวแปร session สำหรับเก็บ log
if "sales_log" not in st.session_state:
    st.session_state.sales_log = []

# ----------------------------
# ส่วน UI เริ่มที่นี่
# ----------------------------

st.title("🧊 ระบบจัดการสินค้าตู้เย็น (เจริญค้า)")

# 🔍 ช่องค้นหาสินค้า
search = st.text_input("ค้นหาชื่อสินค้า")
if search:
    df = df[df["ชื่อสินค้า"].str.contains(search, case=False, na=False)]

# 📋 ตารางแสดงสินค้า
st.dataframe(df, use_container_width=True)

# ----------------------------
# 📦 ฟีเจอร์: ขายสินค้า
# ----------------------------
st.subheader("📦 ขายสินค้า")
selected_items = st.multiselect("เลือกสินค้าที่ขาย", df["ชื่อสินค้า"].tolist())
quantities = {}

for item in selected_items:
    quantities[item] = st.number_input(f"จำนวนที่ขาย - {item}", min_value=1, step=1, key=item)

if st.button("✅ บันทึกยอดขาย"):
    for item in selected_items:
        row = df[df["ชื่อสินค้า"] == item].iloc[0]
        quantity = quantities[item]
        profit_per_unit = row["ราคาขาย"] - row["ต้นทุน"]
        total_profit = profit_per_unit * quantity
        total_sale = row["ราคาขาย"] * quantity
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # บันทึกลง Sheet2
        client.open("สินค้าตู้เย็นปลีก_GS").worksheet("Sheet2").append_row([
            now, item, quantity, row["ราคาขาย"], row["ต้นทุน"],
            total_sale, total_profit, "drink"
        ])

        st.session_state.sales_log.append((item, quantity))

    st.success("✅ บันทึกยอดขายสำเร็จแล้ว")

# 🔁 Undo
if st.button("↩️ ยกเลิกการขายล่าสุด") and st.session_state.sales_log:
    undone = st.session_state.sales_log.pop()
    st.warning(f"⛔ ยกเลิก: {undone[0]} จำนวน {undone[1]} (กรุณาแก้ใน Google Sheet ด้วยตนเอง)")

# ----------------------------
# ➕ เพิ่มสินค้าใหม่
# ----------------------------
st.subheader("➕ เพิ่มสินค้าใหม่")
with st.expander("เพิ่มสินค้า"):
    new_name = st.text_input("ชื่อสินค้าใหม่")
    new_price = st.number_input("ราคาขาย", min_value=0)
    new_cost = st.number_input("ต้นทุน", min_value=0)
    if st.button("📌 เพิ่มสินค้า"):
        profit = new_price - new_cost
        sheet.append_row([new_name, 0, new_price, new_cost, profit])
        st.success("✅ เพิ่มสินค้าเรียบร้อย กรุณารีเฟรชหน้า")

# ----------------------------
# ✏️ แก้ไขสินค้าเดิม
# ----------------------------
st.subheader("✏️ แก้ไขสินค้า")
selected_edit = st.selectbox("เลือกสินค้าที่จะแก้ไข", df["ชื่อสินค้า"].tolist())
edit_row = df[df["ชื่อสินค้า"] == selected_edit].iloc[0]
new_edit_price = st.number_input("แก้ไขราคาขาย", value=int(edit_row["ราคาขาย"]))
new_edit_cost = st.number_input("แก้ไขต้นทุน", value=int(edit_row["ต้นทุน"]))

if st.button("💾 บันทึกการแก้ไข"):
    index = df[df["ชื่อสินค้า"] == selected_edit].index[0] + 2  # +2 เผื่อ header
    profit = new_edit_price - new_edit_cost
    sheet.update(f"C{index}:E{index}", [[new_edit_price, new_edit_cost, profit]])
    st.success("✅ แก้ไขสำเร็จ กรุณารีเฟรชหน้า")

# ----------------------------
# 💰 สรุปยอดขายในรอบ session นี้
# ----------------------------
st.subheader("💰 สรุปยอดขายในรอบนี้")
if st.session_state.sales_log:
    total_sales = 0
    total_profit = 0
    for item, quantity in st.session_state.sales_log:
        row = df[df["ชื่อสินค้า"] == item].iloc[0]
        total_sales += row["ราคาขาย"] * quantity
        total_profit += (row["ราคาขาย"] - row["ต้นทุน"]) * quantity

    st.info(f"💸 ยอดขายรวม: {total_sales:,.2f} บาท\n\n💰 กำไรรวม: {total_profit:,.2f} บาท")
else:
    st.write("ยังไม่มีการขายในรอบนี้")
