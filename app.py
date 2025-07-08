import streamlit as st
import gspread
from google.oauth2 import service_account
from datetime import datetime
import pandas as pd

# ✅ โหลด credentials
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

# ✅ รีเซ็ตยอดเข้า/ออกทุกวันใหม่
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

# ✅ session_state สำหรับตะกร้าขาย
if "cart" not in st.session_state:
    st.session_state.cart = []

# -------------------
# 🛒 ขายสินค้า
# -------------------
st.title("🧊 ระบบขายสินค้า - ร้านเจริญค้า")
st.subheader("🔎 เพิ่มสินค้าเข้าสู่ตะกร้า")

product_names = df["ชื่อสินค้า"].tolist()
product_select = st.selectbox("ค้นหาสินค้า", product_names, index=0)
qty_input = st.number_input("จำนวน", min_value=1, step=1, key="sell_qty")

if st.button("➕ เพิ่มสินค้า"):
    row = df[df["ชื่อสินค้า"] == product_select].iloc[0]
    st.session_state.cart.append({
        "name": product_select,
        "qty": qty_input,
        "price": row["ราคาขาย"],
        "cost": row["ต้นทุน"]
    })
    st.success(f"เพิ่ม {product_select} x {qty_input} แล้ว")

# ✅ แสดงรายการขายทั้งหมด
if st.session_state.cart:
    st.subheader("🧾 รายการขายทั้งหมด")
    total, total_profit = 0, 0
    for item in st.session_state.cart:
        subtotal = item["qty"] * item["price"]
        profit = item["qty"] * (item["price"] - item["cost"])
        total += subtotal
        total_profit += profit
        st.write(f"- {item['name']} x {item['qty']} = {subtotal:.2f} บาท")

    st.info(f"💵 ยอดรวม: {total:.2f} บาท | 🟢 กำไร: {total_profit:.2f} บาท")
    paid = st.number_input("💰 รับเงิน", min_value=0.0, step=1.0, key="paid_input")
    if paid >= total:
        st.success(f"เงินทอน: {paid - total:.2f} บาท")
    else:
        st.warning("ยอดเงินไม่พอ")

    if st.button("✅ ยืนยันการขาย"):
        for item in st.session_state.cart:
            idx = df[df["ชื่อสินค้า"] == item["name"]].index[0] + 2
            sheet.update_cell(idx, 7, int(sheet.cell(idx, 7).value or 0) + item["qty"])
            sheet.update_cell(idx, 5, int(sheet.cell(idx, 5).value or 0) - item["qty"])
            sheet_sales.append_row([
                now_date, item["name"], item["qty"],
                item["qty"] * item["price"],
                item["qty"] * (item["price"] - item["cost"])
            ])
        st.success("✅ บันทึกการขายเรียบร้อยแล้ว")
        # ✅ ล้างข้อมูลตะกร้า
        st.session_state.cart.clear()
        st.session_state.sell_qty = 1
        st.session_state.paid_input = 0.0

# -------------------
# ➕ เติมสินค้า
# -------------------
with st.expander("📦 เติมสินค้า"):
    item_to_add = st.selectbox("เลือกสินค้า", df["ชื่อสินค้า"].tolist(), key="restock_item")
    amount_to_add = st.number_input("จำนวนที่เติม", min_value=1, step=1, key="restock_qty")
    if st.button("✅ เติมเข้า"):
        idx = df[df["ชื่อสินค้า"] == item_to_add].index[0] + 2
        sheet.update_cell(idx, 6, int(sheet.cell(idx, 6).value or 0) + amount_to_add)
        sheet.update_cell(idx, 5, int(sheet.cell(idx, 5).value or 0) + amount_to_add)
        st.success(f"✅ เติมสินค้า {item_to_add} จำนวน {amount_to_add} เรียบร้อยแล้ว")

# -------------------
# ✏️ แก้ไขสินค้า
# -------------------
with st.expander("✏️ แก้ไขสินค้า"):
    edit_item = st.selectbox("เลือกรายการ", df["ชื่อสินค้า"].tolist(), key="edit_select")
    idx = df[df["ชื่อสินค้า"] == edit_item].index[0] + 2
    with st.form("edit_form"):
        new_price = st.number_input("ราคาขายใหม่", value=float(df.loc[idx-2, "ราคาขาย"]))
        new_cost = st.number_input("ต้นทุนใหม่", value=float(df.loc[idx-2, "ต้นทุน"]))
        new_stock = st.number_input("คงเหลือใหม่", value=int(df.loc[idx-2, "คงเหลือ"]), step=1)
        confirm = st.form_submit_button("💾 บันทึก")
        if confirm:
            sheet.update_cell(idx, 3, new_price)
            sheet.update_cell(idx, 4, new_cost)
            sheet.update_cell(idx, 5, new_stock)
            st.success(f"✅ อัปเดต {edit_item} เรียบร้อยแล้ว")
