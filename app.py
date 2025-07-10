import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ตั้งค่า credentials และ spreadsheet
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"],
    scopes=scope
)
gc = gspread.authorize(credentials)
sh = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
sheet = sh.worksheet("ตู้เย็น")

st.set_page_config(page_title="ร้านเจริญค้า", layout="wide")

# โหลดข้อมูล
data = sheet.get_all_records()

# แปลงข้อมูลเป็น dictionary
products = []
for row in data:
    products.append({
        "ชื่อสินค้า": row["ชื่อสินค้า"],
        "ราคาขาย": float(row["ราคาขาย"]),
        "ต้นทุน": float(row["ต้นทุน"]),
        "คงเหลือ": int(row["คงเหลือ"])
    })

# สร้างตัวเลือกสินค้า
product_names = [p["ชื่อสินค้า"] for p in products]
cart = st.session_state.get("cart", {})

st.title("🛒 ร้านเจริญค้า - ระบบขายสินค้า")

selected_products = st.multiselect("🛍️ เลือกสินค้าที่ต้องการ", product_names)

for name in selected_products:
    col1, col2, col3 = st.columns([2,1,1])
    with col1:
        st.markdown(f"**{name}**")
    with col2:
        if st.button("➖", key=f"dec_{name}"):
            cart[name] = max(0, cart.get(name, 0) - 1)
    with col3:
        if st.button("➕", key=f"inc_{name}"):
            cart[name] = cart.get(name, 0) + 1

# ปุ่มเพิ่มลงตะกร้า
if st.button("➕ เพิ่มลงตะกร้า"):
    st.session_state["cart"] = cart

st.markdown("---")
st.subheader("📋 รายการขาย")

total_price = 0
total_profit = 0
for name, qty in cart.items():
    if qty <= 0:
        continue
    product = next((p for p in products if p["ชื่อสินค้า"] == name), None)
    if product:
        line_total = product["ราคาขาย"] * qty
        line_profit = (product["ราคาขาย"] - product["ต้นทุน"]) * qty
        total_price += line_total
        total_profit += line_profit
        st.write(f"- {name} x {qty} = {line_total:.2f} บาท")

st.markdown(f"🧾 ยอดรวม: {total_price:.2f} บาท | 🟢 กำไร: {total_profit:.2f} บาท")

money_received = st.number_input("💰 รับเงิน", min_value=0.0, value=0.0, step=1.0)

if money_received < total_price:
    st.warning("💸 ยอดเงินไม่พอ")
else:
    change = money_received - total_price
    st.success(f"เงินทอน: {change:.2f} บาท")

if st.button("✅ ยืนยันการขาย"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for name, qty in cart.items():
        for i, row in enumerate(data, start=2):
            if row["ชื่อสินค้า"] == name:
                current_out = row["ออก"]
                new_out = current_out + qty
                out_cell = f"G{i}"
                sheet.update(out_cell, [[new_out]])
                break
    st.session_state["cart"] = {}
    st.success("✅ บันทึกยอดขายและรีเซ็ตหน้าเรียบร้อย")
