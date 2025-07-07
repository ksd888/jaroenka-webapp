import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ตั้งค่า credentials ด้วย secrets
import json
from io import StringIO

# โหลด service account จาก secrets
service_account_json = st.secrets["GCP_SERVICE_ACCOUNT"]
creds_dict = json.loads(service_account_json)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# เชื่อม Google Sheet
sheet = client.open("สินค้าตู้เย็นปลีก_GS").worksheet("ตู้เย็น")
data = sheet.get_all_records()
df = pd.DataFrame(data)

# สร้างตัวแปรสถานะการขาย
if "sales_log" not in st.session_state:
    st.session_state.sales_log = []

# หัวเรื่อง
st.title("ระบบจัดการสินค้าตู้เย็น (เจริญค้า) 🧊")

# ค้นหาสินค้า
search = st.text_input("🔍 ค้นหาชื่อสินค้า")
if search:
    df = df[df["ชื่อสินค้า"].str.contains(search, case=False, na=False)]

# แสดงตารางสินค้า
st.dataframe(df, use_container_width=True)

# 📦 บันทึกการขาย
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

        # บันทึกยอดขายไป Sheet2 (ระบุ type เป็น drink)
        client.open("สินค้าตู้เย็นปลีก_GS").worksheet("Sheet2").append_row([
            now, item, quantity, row["ราคาขาย"], row["ต้นทุน"],
            total_sale, total_profit, "drink"
        ])

        # เก็บ log สำหรับ Undo
        st.session_state.sales_log.append((item, quantity))

    st.success("✅ บันทึกยอดขายสำเร็จ")

# 🔁 Undo
if st.button("↩️ Undo การขายล่าสุด") and st.session_state.sales_log:
    undone = st.session_state.sales_log.pop()
    st.warning(f"⛔ ยกเลิกการขาย: {undone[0]} จำนวน {undone[1]} สำเร็จ (โปรดแก้ไขใน Google Sheet ด้วยตนเอง)")

# ➕ เพิ่มสินค้าใหม่
st.subheader("➕ เพิ่มสินค้าใหม่")
with st.expander("คลิกเพื่อเพิ่มสินค้า"):
    new_name = st.text_input("ชื่อสินค้าใหม่")
    new_price = st.number_input("ราคาขาย", min_value=0)
    new_cost = st.number_input("ต้นทุน", min_value=0)
    if st.button("📌 เพิ่มสินค้า"):
        profit = new_price - new_cost
        sheet.append_row([new_name, 0, new_price, new_cost, profit])
        st.success("✅ เพิ่มสินค้าเรียบร้อยแล้ว กรุณารีเฟรชหน้า")

# ✏️ แก้ไขสินค้า
st.subheader("✏️ แก้ไขสินค้าเดิม")
selected_edit = st.selectbox("เลือกสินค้าที่จะแก้ไข", df["ชื่อสินค้า"].tolist())
edit_row = df[df["ชื่อสินค้า"] == selected_edit].iloc[0]
new_edit_price = st.number_input("แก้ไขราคาขาย", value=int(edit_row["ราคาขาย"]))
new_edit_cost = st.number_input("แก้ไขต้นทุน", value=int(edit_row["ต้นทุน"]))

if st.button("💾 บันทึกการแก้ไข"):
    index = df[df["ชื่อสินค้า"] == selected_edit].index[0] + 2  # +2 เพราะมี header
    profit = new_edit_price - new_edit_cost
    sheet.update(f"C{index}:E{index}", [[new_edit_price, new_edit_cost, profit]])
    st.success("📝 แก้ไขข้อมูลเรียบร้อย กรุณารีเฟรชหน้า")

# 💰 สรุปยอดขายทั้งหมดใน session
st.subheader("💰 สรุปยอดขายในรอบนี้")
if st.session_state.sales_log:
    total_items = sum(q for _, q in st.session_state.sales_log)
    total_profit = 0
    total_sales = 0
    for item, quantity in st.session_state.sales_log:
        row = df[df["ชื่อสินค้า"] == item].iloc[0]
        total_sales += row["ราคาขาย"] * quantity
        total_profit += (row["ราคาขาย"] - row["ต้นทุน"]) * quantity

    st.markdown(f"**🛒 ยอดขายรวม: {total_sales} บาท**")
    st.markdown(f"**📈 กำไรสุทธิ: {total_profit} บาท**")
else:
    st.info("ยังไม่มีการขายในรอบนี้")
