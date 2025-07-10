import streamlit as st
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials

# ========== เชื่อมต่อ Google Sheet ==========
scope = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"],
    scopes=scope
)
gc = gspread.authorize(credentials)
sh = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
sheet = sh.worksheet("ตู้เย็น")
sales_sheet = sh.worksheet("ยอดขาย")
meta_sheet = sh.worksheet("Meta")

# ========== ฟังก์ชันสำหรับความปลอดภัย ==========
def safe_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0

# ========== โหลดข้อมูลสินค้า ==========
data = sheet.get_all_records()
products = [
    {
        "ชื่อ": row["ชื่อ"],
        "ราคาขาย": safe_float(row["ราคาขาย"]),
        "ต้นทุน": safe_float(row["ต้นทุน"]),
        "คงเหลือ": safe_float(row["คงเหลือ"]),
        "เข้า": safe_float(row["เข้า"]),
        "ออก": safe_float(row["ออก"])
    }
    for row in data
]

# ========== โหลดวันที่ล่าสุด ==========
now_date = datetime.now().strftime("%Y-%m-%d")
meta_sheet.update("B1", [[now_date]])

# ========== UI: Header ==========
st.title("🧊 ระบบขายสินค้า - ร้านเจริญค้า")
st.header("🛒 เลือกสินค้า")

# ========== UI: Autocomplete ค้นหา ==========
product_names = [p["ชื่อ"] for p in products]
selected_names = st.multiselect("🔍 เลือกสินค้าจากชื่อ", product_names)

# ========== ตะกร้าสินค้า ==========
if "cart" not in st.session_state:
    st.session_state.cart = {}

for name in selected_names:
    col1, col2, col3 = st.columns([3,1,1])
    col1.markdown(f"**{name}**")
    if col2.button("➖", key=f"dec_{name}"):
        st.session_state.cart[name] = max(st.session_state.cart.get(name, 0) - 1, 0)
    if col3.button("➕", key=f"inc_{name}"):
        st.session_state.cart[name] = st.session_state.cart.get(name, 0) + 1

# ========== ปุ่มเพิ่มตะกร้า ==========
if st.button("➕ เพิ่มลงตะกร้า"):
    for name in selected_names:
        st.session_state.cart[name] = st.session_state.cart.get(name, 0) + 1

# ========== แสดงรายการขาย ==========
st.subheader("📋 รายการขาย")
total = 0
profit = 0
for name, qty in st.session_state.cart.items():
    if qty > 0:
        prod = next((p for p in products if p["ชื่อ"] == name), None)
        if prod:
            price = prod["ราคาขาย"]
            cost = prod["ต้นทุน"]
            line_total = qty * price
            line_profit = qty * (price - cost)
            total += line_total
            profit += line_profit
            st.markdown(f"- {name} x {qty} = {line_total:.2f} บาท")

st.markdown(f"""<div style="background-color:#123456;padding:10px;border-radius:10px">
💵 <b>ยอดรวม:</b> {total:.2f} บาท | 🟢 <b>กำไร:</b> {profit:.2f} บาท
</div>""", unsafe_allow_html=True)

# ========== รับเงิน / คำนวณเงินทอน ==========
cash = st.number_input("💰 รับเงิน", min_value=0.0, value=0.0, step=1.0)
change = cash - total

if change < 0:
    st.warning("💸 ยอดเงินไม่พอ")
else:
    st.success(f"💵 เงินทอน: {change:.2f} บาท")

# ========== บันทึกยอดขาย ==========
if st.button("✅ ยืนยันการขาย"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for name, qty in st.session_state.cart.items():
        if qty > 0:
            prod = next((p for p in products if p["ชื่อ"] == name), None)
            if prod:
                row_index = next(i for i, row in enumerate(data) if row["ชื่อ"] == name) + 2
                out_cell = f"G{row_index}"
                remain_cell = f"D{row_index}"
                new_out = prod["ออก"] + qty
                new_remain = prod["คงเหลือ"] - qty
                sheet.update(out_cell, new_out)
                sheet.update(remain_cell, new_remain)

                # บันทึกไปตารางยอดขาย
                sales_sheet.append_row([
                    timestamp, name, qty, prod["ราคาขาย"], prod["ต้นทุน"],
                    qty * prod["ราคาขาย"], qty * (prod["ราคาขาย"] - prod["ต้นทุน"]), "drink"
                ])

    st.session_state.cart = {}  # ✅ รีเซ็ตตะกร้า
    st.success("✅ บันทึกยอดขายและรีเซ็ตหน้าสำเร็จแล้ว")
