import streamlit as st
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials

# เชื่อมต่อ Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"],
    scopes=scope
)
gc = gspread.authorize(creds)
sheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE").worksheet("ตู้เย็น")

# Session state
if "cart" not in st.session_state:
    st.session_state.cart = []

# UI ส่วนเพิ่มสินค้า
st.title("🛒 ระบบขายสินค้า")
with st.form("add_to_cart"):
    name = st.text_input("ชื่อสินค้า")
    qty = st.number_input("จำนวน", min_value=1, step=1)
    submitted = st.form_submit_button("➕ เพิ่มลงตะกร้า")
    if submitted:
        st.session_state.cart.append({"name": name, "qty": qty})

# รายการสินค้าในตะกร้า
if st.session_state.cart:
    st.subheader("📋 รายการขาย")
    total = 0
    profit = 0
    for item in st.session_state.cart:
        name = item["name"]
        qty = item["qty"]
        try:
            cell = sheet.find(name)
            row = sheet.row_values(cell.row)
            price = float(row[1])
            cost = float(row[2])
            line_total = price * qty
            total += line_total
            profit += (price - cost) * qty
            st.markdown(f"- {name} x {qty} = {line_total:.2f} บาท")
        except:
            st.warning(f"❗ ไม่พบสินค้า: {name}")

    st.info(f"💰 ยอดรวม: {total:.2f} บาท | 🟢 กำไร: {profit:.2f} บาท")

    money = st.number_input("💴 รับเงิน", min_value=0.0, step=1.0)
    if money < total:
        st.error("🧾 ยอดเงินไม่พอ")
    else:
        change = money - total
        if money > 0:
            st.success(f"💵 เงินทอน: {change:.2f} บาท")

    if st.button("✅ ยืนยันการขาย"):
        for item in st.session_state.cart:
            name = item["name"]
            qty = item["qty"]
            try:
                cell = sheet.find(name)
                if cell:
                    row_idx = cell.row
                    out_cell = f"H{row_idx}"
                    remain_cell = f"I{row_idx}"
                    prev_out = sheet.acell(out_cell).value or "0"
                    prev_remain = sheet.acell(remain_cell).value or "0"
                    new_out = int(prev_out) + qty
                    new_remain = int(prev_remain) - qty
                    sheet.update(out_cell, [[new_out]])
                    sheet.update(remain_cell, [[new_remain]])
            except:
                pass

        # บันทึกยอดขาย
        sale_sheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE").worksheet("ยอดขาย")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sale_sheet.append_row([now, " | ".join([f'{i["name"]} x{i["qty"]}' for i in st.session_state.cart]), total, profit])

        st.success("✅ บันทึกและรีเซ็ตเรียบร้อย")
        st.session_state.cart = []

