import streamlit as st
import gspread
from google.oauth2 import service_account
from datetime import datetime
import pandas as pd

# ✅ โหลด credentials จาก secrets.toml
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive.file",
         "https://www.googleapis.com/auth/drive"]

creds = service_account.Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope)
client = gspread.authorize(creds)

# ✅ เปิด Google Sheet
spreadsheet = client.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
sheet = spreadsheet.worksheet("ตู้เย็น")
sheet_meta = spreadsheet.worksheet("Meta")
sheet_sales = spreadsheet.worksheet("ยอดขาย")

# ✅ รีเซ็ตยอดเข้า/ออกเมื่อวันใหม่
now_date = datetime.now().strftime("%Y-%m-%d")
last_date = sheet_meta.acell("B1").value
if last_date != now_date:
    sheet.batch_update([{
        'range': 'F2:G1000',
        'values': [[0, 0]] * 999
    }])
    sheet_meta.update("B1", [[now_date]])

# ✅ โหลดข้อมูล
data = sheet.get_all_records()
df = pd.DataFrame(data)

# ✅ Session state
if "cart" not in st.session_state:
    st.session_state.cart = []
if "add_qty" not in st.session_state:
    st.session_state.add_qty = 1
if "add_name" not in st.session_state:
    st.session_state.add_name = ""

# ✅ UI
st.title("🧊 ระบบขายสินค้า - ร้านเจริญค้า")
st.header("🛒 ขายสินค้า (เพิ่มทีละหลายรายการ)")

product_names = df["ชื่อสินค้า"].tolist()
product_names_sorted = sorted(product_names)

# 🔎 ค้นหาสินค้าแบบ autocomplete
col1, col2 = st.columns([3, 1])
with col1:
    selected_product = st.text_input("🔍 พิมพ์ชื่อสินค้า", key="add_name")
with col2:
    selected_qty = st.number_input("จำนวน", min_value=1, step=1, key="add_qty")

if st.button("➕ เพิ่มลงตะกร้า"):
    if selected_product in product_names:
        item = df[df["ชื่อสินค้า"] == selected_product].iloc[0]
        st.session_state.cart.append({
            "name": selected_product,
            "qty": selected_qty,
            "price": item["ราคาขาย"],
            "cost": item["ต้นทุน"]
        })
        st.success(f"เพิ่ม {selected_product} x {selected_qty} แล้ว")
        st.session_state.add_name = ""
        st.session_state.add_qty = 1
    else:
        st.warning("กรุณาพิมพ์ชื่อสินค้าที่มีอยู่")

# 📋 แสดงตะกร้า
if st.session_state.cart:
    st.subheader("🧾 รายการขาย")
    total, profit_total = 0, 0
    for item in st.session_state.cart:
        subtotal = item["qty"] * item["price"]
        profit = item["qty"] * (item["price"] - item["cost"])
        total += subtotal
        profit_total += profit
        st.write(f"- {item['name']} x {item['qty']} = {subtotal} บาท")

    st.info(f"💵 ยอดรวม: {total} บาท | 🟢 กำไร: {profit_total} บาท")
    paid = st.number_input("💰 รับเงิน", min_value=0.0, step=1.0, key="paid_input")
    if paid >= total:
        st.success(f"เงินทอน: {paid - total:.2f} บาท")
    else:
        st.warning("ยอดเงินไม่พอ")

    if st.button("✅ ยืนยันการขาย"):
        from math import isnan
        for item in st.session_state.cart:
            idx = df[df["ชื่อสินค้า"] == item["name"]].index[0] + 2
            qty = int(item["qty"])
            price = float(item["price"])
            cost = float(item["cost"])
            subtotal = round(qty * price, 2)
            profit = round(qty * (price - cost), 2)

            sheet.update_cell(idx, 7, int(sheet.cell(idx, 7).value or 0) + qty)
            sheet.update_cell(idx, 5, int(sheet.cell(idx, 5).value or 0) - qty)

            # ✅ แปลงค่าก่อนบันทึกเพื่อเลี่ยง JSON error
            sheet_sales.append_row([
                now_date,
                str(item["name"]),
                int(qty),
                float(subtotal),
                float(profit)
            ])
        st.success("✅ บันทึกยอดขายเรียบร้อยแล้ว")
        st.session_state.cart = []

# ------------------------
# 📦 เติมสินค้า
# ------------------------
with st.expander("➕ เติมสินค้า"):
    selected_item = st.selectbox("เลือกสินค้า", product_names, key="restock_item")
    add_amount = st.number_input("จำนวนที่เติม", min_value=1, step=1, key="restock_qty")
    if st.button("📦 เติมเข้า"):
        idx = df[df["ชื่อสินค้า"] == selected_item].index[0] + 2
        sheet.update_cell(idx, 6, int(sheet.cell(idx, 6).value or 0) + add_amount)
        sheet.update_cell(idx, 5, int(sheet.cell(idx, 5).value or 0) + add_amount)
        st.success(f"✅ เติม {selected_item} จำนวน {add_amount} เรียบร้อย")

# ------------------------
# ✏️ แก้ไขสินค้า
# ------------------------
with st.expander("✏️ แก้ไขสินค้า"):
    edit_item = st.selectbox("เลือกรายการ", product_names, key="edit_item")
    idx = df[df["ชื่อสินค้า"] == edit_item].index[0] + 2
    default_row = df[df["ชื่อสินค้า"] == edit_item].iloc[0]
    new_price = st.number_input("ราคาขายใหม่", value=float(default_row["ราคาขาย"]), key="edit_price")
    new_cost = st.number_input("ต้นทุนใหม่", value=float(default_row["ต้นทุน"]), key="edit_cost")
    new_stock = st.number_input("คงเหลือใหม่", value=int(default_row["คงเหลือ"]), step=1, key="edit_stock")
    if st.button("💾 บันทึกการแก้ไข"):
        sheet.update_cell(idx, 3, new_price)
        sheet.update_cell(idx, 4, new_cost)
        sheet.update_cell(idx, 5, new_stock)
        st.success(f"✅ แก้ไข {edit_item} เรียบร้อย")
