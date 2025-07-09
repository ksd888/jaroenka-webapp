
import streamlit as st
import datetime
import gspread
from google.oauth2.service_account import Credentials

# เชื่อมต่อ Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope
)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
worksheet = sheet.worksheet("ตู้เย็น")

# โหลดข้อมูล
data = worksheet.get_all_records()
product_dict = {row["ชื่อสินค้า"]: row for row in data}

# ฟังก์ชันปลอดภัย
def safe_int(val):
    try:
        return int(val)
    except:
        return 0

def safe_float(val):
    try:
        return float(val)
    except:
        return 0.0

# เริ่มต้น session_state
for key in ["cart", "selected_products", "quantities", "paid_input", "sale_confirmed"]:
    if key not in st.session_state:
        st.session_state[key] = [] if key == "cart" else {} if key == "quantities" else 0.0 if key == "paid_input" else False if key == "sale_confirmed" else []

# UI
st.title("🧊 ระบบขายสินค้า - ร้านเจริญค้า")
st.subheader("🛒 ขายสินค้า (เลือกหลายรายการพร้อมกัน)")

selected = st.multiselect("🔍 เลือกสินค้าจากชื่อ", options=list(product_dict.keys()), default=st.session_state.selected_products)
for product in selected:
    if product not in st.session_state.quantities:
        st.session_state.quantities[product] = 1

    cols = st.columns([2, 1, 1])
    with cols[0]:
        st.markdown(f"**จำนวน - {product}**")
    with cols[1]:
        if st.button("➖", key=f"dec_{product}"):
            st.session_state.quantities[product] = max(1, st.session_state.quantities[product] - 1)
    with cols[2]:
        if st.button("➕", key=f"inc_{product}"):
            st.session_state.quantities[product] += 1

# เพิ่มลงตะกร้า
if st.button("➕ เพิ่มลงตะกร้า"):
    for product in selected:
        qty = safe_int(st.session_state.quantities[product])
        if qty > 0:
            st.session_state.cart.append((product, qty))
    st.success("✅ เพิ่มสินค้าลงตะกร้าเรียบร้อยแล้ว")

# แสดงตะกร้า
if st.session_state.cart:
    st.subheader("🧾 รายการขาย")
    total_price = 0
    total_profit = 0
    for item, qty in st.session_state.cart:
        row = product_dict[item]
        price = safe_int(row["ราคาขาย"])
        cost = safe_int(row["ต้นทุน"])
        profit = (price - cost) * qty
        st.markdown(f"- {item} x {qty} = {price * qty:.2f} บาท")
        total_price += price * qty
        total_profit += profit

    st.info(f"💳 ยอดรวม: {total_price:.2f} บาท | 🟢 กำไร: {total_profit:.2f} บาท")

    # รับเงิน
    st.session_state.paid_input = st.number_input("💰 รับเงิน", value=st.session_state.paid_input, step=1.0)
    if st.session_state.paid_input < total_price:
        st.warning("💸 ยอดเงินไม่พอ")
    else:
        if st.button("✅ ยืนยันการขาย"):
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for item, qty in st.session_state.cart:
                row = product_dict[item]
                row_id = row["ID"]  # ต้องมีคอลัมน์ ID
                col_out = list(data[0].keys()).index("ออก")
                col_left = list(data[0].keys()).index("คงเหลือในตู้")

                # อัปเดตยอด
                old_out = safe_int(row["ออก"])
                old_left = safe_int(row["คงเหลือในตู้"])
                new_out = old_out + qty
                new_left = old_left - qty
                worksheet.update_cell(int(row_id)+2, col_out+1, new_out)
                worksheet.update_cell(int(row_id)+2, col_left+1, new_left)

            # บันทึกยอดขาย
            summary_ws = sheet.worksheet("ยอดขาย")
            summary_ws.append_row([
                now,
                ", ".join([f"{i} x {q}" for i, q in st.session_state.cart]),
                total_price,
                total_profit,
                st.session_state.paid_input,
                st.session_state.paid_input - total_price,
                "drink"
            ])

            st.success("✅ บันทึกยอดขายเรียบร้อยแล้ว")
            st.session_state.cart = []
            st.session_state.selected_products = []
            st.session_state.quantities = {}
            st.session_state.paid_input = 0.0

# เติมสินค้า
with st.expander("📦 เติมสินค้า"):
    selected_item = st.selectbox("เลือกสินค้าเพื่อเติม", list(product_dict.keys()), key="restock_item")
    add_qty = st.number_input("จำนวนที่เติม", min_value=1, step=1, key="restock_qty")
    if st.button("📥 ยืนยันการเติม"):
        row = product_dict[selected_item]
        row_id = int(row["ID"])
        current_in = safe_int(row["เข้า"])
        current_left = safe_int(row["คงเหลือในตู้"])
        col_in = list(data[0].keys()).index("เข้า")
        col_left = list(data[0].keys()).index("คงเหลือในตู้")
        worksheet.update_cell(row_id+2, col_in+1, current_in + add_qty)
        worksheet.update_cell(row_id+2, col_left+1, current_left + add_qty)
        st.success("✅ เติมสินค้าเรียบร้อยแล้ว")

# แก้ไขสินค้า
with st.expander("✏️ แก้ไขสินค้า"):
    edit_item = st.selectbox("เลือกรายการสินค้า", list(product_dict.keys()), key="edit_item")
    row = product_dict[edit_item]
    row_id = int(row["ID"])
    new_price = st.number_input("ราคาขายใหม่", value=safe_float(row["ราคาขาย"]), key="edit_price")
    new_cost = st.number_input("ต้นทุนใหม่", value=safe_float(row["ต้นทุน"]), key="edit_cost")
    new_stock = st.number_input("คงเหลือใหม่", value=safe_int(row["คงเหลือในตู้"]), key="edit_stock")

    if st.button("💾 บันทึกการแก้ไข"):
        col_price = list(data[0].keys()).index("ราคาขาย")
        col_cost = list(data[0].keys()).index("ต้นทุน")
        col_stock = list(data[0].keys()).index("คงเหลือในตู้")
        worksheet.update_cell(row_id+2, col_price+1, new_price)
        worksheet.update_cell(row_id+2, col_cost+1, new_cost)
        worksheet.update_cell(row_id+2, col_stock+1, new_stock)
        st.success("✅ อัปเดตสินค้าเรียบร้อยแล้ว")
