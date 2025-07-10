import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime

# ✅ เชื่อมต่อ Google Sheet
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope
)
gc = gspread.authorize(credentials)
spreadsheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
sheet = spreadsheet.worksheet("ตู้เย็น")
sales_sheet = spreadsheet.worksheet("ยอดขาย")
meta_sheet = spreadsheet.worksheet("Meta")

# ✅ โหลดข้อมูลสินค้า
data = sheet.get_all_records()
items = {row["ชื่อสินค้า"]: row for row in data}

# ✅ กำหนด state สำหรับตะกร้าและเงิน
if "cart" not in st.session_state:
    st.session_state.cart = []

if "cash_received" not in st.session_state:
    st.session_state.cash_received = 0.0

# ✅ ค้นหาสินค้าและเพิ่มลงตะกร้า
st.title("🛒 ระบบขายหน้าร้าน - เจริญค้า")

st.subheader("🧃 เลือกสินค้า")
product_options = list(items.keys())
selected_products = st.multiselect("🔘 เลือกสินค้าจากชื่อ", product_options)

for product in selected_products:
    col1, col2 = st.columns([1, 1])
    with col1:
        st.write(product)
    with col2:
        qty = st.number_input(f"จำนวน {product}", min_value=0, key=f"qty_{product}")
        if st.button("➕ เพิ่มลงตะกร้า", key=f"add_{product}"):
            st.session_state.cart.append({"name": product, "qty": qty})

# ✅ แสดงตะกร้าสินค้า
st.markdown("## 📋 รายการขาย")
total = 0
profit = 0
for item in st.session_state.cart:
    name = item["name"]
    qty = item["qty"]
    price = items[name]["ราคาขาย"]
    cost = items[name]["ต้นทุน"]
    line_total = price * qty
    line_profit = (price - cost) * qty
    total += line_total
    profit += line_profit
    st.markdown(f"- {name} x {qty} = {line_total:.2f} บาท")

st.info(f"💵 ยอดรวม: {total:.2f} บาท | 🟢 กำไร: {profit:.2f} บาท")

# ✅ รับเงินและแสดงเงินทอน
st.subheader("💰 รับเงิน")
st.session_state.cash_received = st.number_input("💲 รับเงิน", min_value=0.0, value=st.session_state.cash_received, step=1.0)

change = st.session_state.cash_received - total
if change < 0:
    st.warning("💸 ยอดเงินไม่พอ")
else:
    st.success(f"เงินทอน: {change:.2f} บาท")

# ✅ ปุ่มยืนยันการขาย
if st.button("✅ ยืนยันการขาย"):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for item in st.session_state.cart:
        name = item["name"]
        qty = item["qty"]
        price = items[name]["ราคาขาย"]
        cost = items[name]["ต้นทุน"]
        profit_unit = price - cost
        sales_sheet.append_row([
            now, name, qty, price, cost, price * qty, profit_unit * qty, "drink"
        ])

        # อัปเดตจำนวนคงเหลือในชีท
        for i, row in enumerate(data, start=2):  # เริ่มที่ row 2
            if row["ชื่อสินค้า"] == name:
                current_out = row["ออก"]
                new_out = current_out + qty
                out_cell = f"G{i}"
                sheet.update(out_cell, new_out)
                break

    st.success("✅ บันทึกยอดขายและรีเซ็ตหน้าสำเร็จแล้ว")

    # 🔁 รีเซ็ตตะกร้าและเงินรับ
    st.session_state.cart = []
    st.session_state.cash_received = 0.0

    # 🚀 รีโหลดใหม่ทันที
    st.experimental_rerun()
