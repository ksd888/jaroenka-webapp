
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime

# ✅ ใช้ secrets สำหรับ Streamlit
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope)
gc = gspread.authorize(credentials)

# ✅ เปิดชีท
spreadsheet_id = "1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE"
sheet = gc.open_by_key(spreadsheet_id).worksheet("ตู้เย็น")

# ✅ โหลดข้อมูลจาก Google Sheet
data = sheet.get_all_records()

# ✅ ฟังก์ชันป้องกัน float error
def safe_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0

# ✅ เตรียมสินค้าแบบปลอดภัย
products = []
for row in data:
    if "ชื่อ" in row:
        products.append({
            "ชื่อ": row.get("ชื่อ", ""),
            "ราคาขาย": safe_float(row.get("ราคาขาย")),
            "ต้นทุน": safe_float(row.get("ต้นทุน")),
            "คงเหลือ": safe_float(row.get("คงเหลือ")),
            "เข้า": safe_float(row.get("เข้า")),
            "ออก": safe_float(row.get("ออก")),
        })

# ✅ เริ่มต้น Streamlit UI
st.title("🧊 ระบบขายสินค้า - ร้านเจริญค้า")

# ✅ ค้นหาและเลือกสินค้า
selected = st.multiselect("🔍 เลือกสินค้าที่จะขาย", [p["ชื่อ"] for p in products])
cart = {name: 0 for name in selected}

for name in selected:
    col1, col2, col3 = st.columns([3,1,1])
    with col1:
        st.write(name)
    with col2:
        if st.button("-", key=f"dec_{name}"):
            cart[name] = max(cart[name] - 1, 0)
    with col3:
        if st.button("+", key=f"inc_{name}"):
            cart[name] += 1

# ✅ ปุ่มเพิ่มลงตะกร้า
if st.button("➕ เพิ่มลงตะกร้า"):
    st.session_state["cart"] = cart.copy()

# ✅ แสดงตะกร้า
st.subheader("📋 รายการขาย")
cart = st.session_state.get("cart", {})
total = 0.0
profit = 0.0

for name, qty in cart.items():
    for p in products:
        if p["ชื่อ"] == name:
            price = p["ราคาขาย"]
            cost = p["ต้นทุน"]
            subtotal = qty * price
            gain = qty * (price - cost)
            total += subtotal
            profit += gain
            st.write(f"- {name} x {qty} = {subtotal:.2f} บาท")
            break

st.markdown(f"💵 **ยอดรวม:** {total:.2f} บาท | 🟢 **กำไร:** {profit:.2f} บาท")

# ✅ รับเงิน และคำนวณเงินทอน
amount = st.number_input("💰 รับเงิน", min_value=0.0, step=1.0)
if amount < total:
    st.warning("💸 ยอดเงินไม่พอ")
else:
    change = amount - total
    st.success(f"เงินทอน: {change:.2f} บาท")

# ✅ ยืนยันการขาย
if st.button("✅ ยืนยันการขาย"):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for name, qty in cart.items():
        for i, row in enumerate(data):
            if row.get("ชื่อ") == name:
                out_cell = f"G{i+2}"
                new_out = row.get("ออก", 0) + qty
                sheet.update(out_cell, [[new_out]])
                break
    st.session_state["cart"] = {}  # ✅ รีเซ็ตตะกร้า
    st.success("✅ บันทึกยอดขายและรีเซ็ตหน้าเรียบร้อย")
