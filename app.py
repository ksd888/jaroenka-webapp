import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# เชื่อมต่อ Google Sheet
scope = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"],
    scopes=scope
)
gc = gspread.authorize(credentials)
spreadsheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
sheet = spreadsheet.worksheet("ตู้เย็น")
sales_sheet = spreadsheet.worksheet("ยอดขาย")
meta_sheet = spreadsheet.worksheet("Meta")

# ดึงข้อมูลสินค้าทั้งหมด
rows = sheet.get_all_records()
products = {row["ชื่อสินค้า"]: row for row in rows}

# เตรียมค่าใน session_state
if "cart" not in st.session_state:
    st.session_state.cart = []
if "sale_records" not in st.session_state:
    st.session_state.sale_records = []
if "selected_items" not in st.session_state:
    st.session_state.selected_items = []
if "received_money" not in st.session_state:
    st.session_state.received_money = 0.0

# UI
st.title("🧊 ระบบขายสินค้า - ร้านเจริญค้า")
st.subheader("🛒 เลือกสินค้า")

product_name = st.selectbox("🔍 เลือกสินค้าจากชื่อ", [""] + list(products.keys()))
if product_name:
    if st.button("➕ เพิ่มลงตะกร้า"):
        existing = next((item for item in st.session_state.cart if item["name"] == product_name), None)
        if existing:
            existing["qty"] += 1
        else:
            st.session_state.cart.append({"name": product_name, "qty": 1})

# แสดงตะกร้า
if st.session_state.cart:
    st.markdown("### 📋 รายการขาย")
    total = 0
    profit = 0
    for item in st.session_state.cart:
        name = item["name"]
        qty = item["qty"]
        price = float(products[name]["ราคาขาย"])
        cost = float(products[name]["ต้นทุน"])
        st.write(f"- {name} x {qty} = {qty * price:.2f} บาท")
        total += qty * price
        profit += qty * (price - cost)

    st.info(f"💸 ยอดรวม: {total:.2f} บาท | 🟢 กำไร: {profit:.2f} บาท")

    st.subheader("💰 รับเงิน")
    received = st.number_input("ใส่จำนวนเงิน", value=st.session_state.received_money, key="money_input")
    st.session_state.received_money = received
    change = received - total
    if change < 0:
        st.warning("💰 ยอดเงินไม่พอ")
    else:
        st.success(f"เงินทอน: {change:.2f} บาท")

    # ยืนยันการขายด้วยปุ่ม (ไม่ใช้ checkbox)
    if st.button("✅ ยืนยันการขาย"):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for item in st.session_state.cart:
            name = item["name"]
            qty = item["qty"]
            price = float(products[name]["ราคาขาย"])
            cost = float(products[name]["ต้นทุน"])
            sales_sheet.append_row([
                now, name, qty, price, cost, qty * price, qty * (price - cost), "drink"
            ])

            # อัปเดตคงเหลือและออกในชีท
            cell = sheet.find(name)
            if cell:
                row_num = cell.row
                out_val = sheet.cell(row_num, 8).value
                remain_val = sheet.cell(row_num, 9).value
                new_out = int(out_val) + qty if out_val else qty
                new_remain = int(remain_val) - qty if remain_val else 0
                sheet.update(f"H{row_num}", new_out)
                sheet.update(f"I{row_num}", new_remain)

        st.success("✅ บันทึกยอดขายและรีเซ็ตหน้าสำเร็จแล้ว")

        # รีเซ็ตค่าทันทีหลังบันทึก
        st.session_state.cart = []
        st.session_state.sale_records = []
        st.session_state.selected_items = []
        st.session_state.received_money = 0.0
