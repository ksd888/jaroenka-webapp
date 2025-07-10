import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime

# ✅ เชื่อมต่อ Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope)
gc = gspread.authorize(credentials)
sh = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
sheet = sh.worksheet("ตู้เย็น")
sales_sheet = sh.worksheet("ยอดขาย")

# ✅ ฟังก์ชันแปลง float แบบปลอดภัย
def safe_float(val):
    try:
        return float(val)
    except:
        return 0.0

# ✅ โหลดข้อมูลสินค้า
data = sheet.get_all_records()
products = []
for row in data:
    try:
        products.append({
            "ชื่อ": row.get("ชื่อ", ""),
            "ราคาขาย": safe_float(row.get("ราคาขาย")),
            "ต้นทุน": safe_float(row.get("ต้นทุน")),
            "คงเหลือ": int(row.get("คงเหลือ", 0)),
            "ออก": int(row.get("ออก", 0)),
        })
    except Exception as e:
        st.warning(f"พบข้อผิดพลาดในข้อมูลสินค้า: {e}")

# ✅ UI
st.title("🧊 ระบบขายสินค้า - ร้านเจริญค้า")

cart = st.session_state.get("cart", {})
selected = st.multiselect("🔍 เลือกสินค้าที่จะขาย", [p["ชื่อ"] for p in products])
for name in selected:
    col1, col2, col3 = st.columns([2,1,1])
    with col1:
        st.markdown(f"**{name}**")
    with col2:
        if st.button("-", key=f"dec_{name}"):
            cart[name] = max(cart.get(name, 0) - 1, 0)
    with col3:
        if st.button("+", key=f"inc_{name}"):
            cart[name] = cart.get(name, 0) + 1

# ✅ เพิ่มลงตะกร้า
if st.button("➕ เพิ่มลงตะกร้า"):
    st.session_state.cart = cart

# ✅ แสดงตะกร้า
st.markdown("## 📋 รายการขาย")
total = 0
profit = 0
for name, qty in cart.items():
    prod = next((p for p in products if p["ชื่อ"] == name), None)
    if prod:
        subtotal = prod["ราคาขาย"] * qty
        gain = (prod["ราคาขาย"] - prod["ต้นทุน"]) * qty
        st.markdown(f"- {name} x {qty} = {subtotal:.2f} บาท")
        total += subtotal
        profit += gain

st.info(f"💵 ยอดรวม: {total:.2f} บาท | 🟢 กำไร: {profit:.2f} บาท")

# ✅ รับเงิน
received = st.number_input("💰 รับเงิน", min_value=0.0, format="%.2f")
change = received - total
st.success(f"เงินทอน: {change:.2f} บาท")

# ✅ ยืนยันการขาย
if st.button("✅ ยืนยันการขาย"):
    if received < total:
        st.warning("💸 ยอดเงินไม่พอ")
    else:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for name, qty in cart.items():
            prod = next((p for p in products if p["ชื่อ"] == name), None)
            if prod:
                # อัปเดตยอดในตาราง
                idx = next(i+2 for i,r in enumerate(data) if r["ชื่อ"] == name)
                new_out = prod["ออก"] + qty
                new_stock = prod["คงเหลือ"] - qty
                sheet.update(f"G{idx}", [[new_out]])
                sheet.update(f"E{idx}", [[new_stock]])
                # บันทึกยอดขาย
                sales_sheet.append_row([now, name, qty, prod["ราคาขาย"], prod["ต้นทุน"], total, profit, "drink"])
        st.success("✅ บันทึกยอดขายและรีเซ็ตหน้าสำเร็จแล้ว")
        st.session_state.cart = {}

# ✅ ปุ่มล้างตะกร้า
if st.button("🧹 ล้างตะกร้าสินค้า"):
    st.session_state.cart = {}
    st.success("ตะกร้าถูกล้างแล้ว")
