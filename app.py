import streamlit as st
import gspread
from google.oauth2 import service_account
from datetime import datetime
import pandas as pd

# ✅ โหลด credentials
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]
creds = service_account.Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope)
client = gspread.authorize(creds)

# ✅ เปิด Google Sheet
spreadsheet = client.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
sheet = spreadsheet.worksheet("ตู้เย็น")
sheet_meta = spreadsheet.worksheet("Meta")
sheet_sales = spreadsheet.worksheet("ยอดขาย")

# ✅ รีเซ็ตเข้า/ออกทุกวัน
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
product_names = sorted(df["ชื่อสินค้า"].tolist())

# ✅ Session state
for key, default in {
    "cart": [],
    "add_qty": 1,
    "input_name": "",
    "paid_input": 0.0
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ✅ UI
st.title("🧊 ระบบขายสินค้า - ร้านเจริญค้า")
st.header("🛒 ขายสินค้า (พิมพ์ชื่อ + กด ➕)")

user_input = st.text_input("🔍 ค้นหาสินค้า", st.session_state["input_name"])

# 🔍 แนะนำคำ autocomplete
suggestions = [p for p in product_names if user_input.strip().lower() in p.lower()]
if suggestions and user_input.strip():
    st.caption("📌 คลิกเพื่อเลือกชื่อสินค้า:")
    for s in suggestions[:5]:
        if st.button(f"➤ {s}", key=f"sugg_{s}"):
            st.session_state["input_name"] = s
            st.experimental_rerun()

qty = st.number_input("จำนวน", min_value=1, step=1, key="add_qty")

# ➕ เพิ่มลงตะกร้า
if st.button("➕ เพิ่มลงตะกร้า"):
    match = [p for p in product_names if p.lower() == user_input.strip().lower()]
    if match:
        selected_product = match[0]
        row = df[df["ชื่อสินค้า"] == selected_product].iloc[0]
        st.session_state["cart"].append({
            "name": selected_product,
            "qty": qty,
            "price": float(row["ราคาขาย"]),
            "cost": float(row["ต้นทุน"])
        })
        st.session_state["input_name"] = ""
        st.session_state["add_qty"] = 1
        st.experimental_rerun()
    else:
        st.warning("❌ ไม่พบสินค้าที่พิมพ์")

# 🧾 แสดงตะกร้า
if st.session_state["cart"]:
    st.subheader("📋 รายการขาย")
    total = sum(i["qty"] * i["price"] for i in st.session_state["cart"])
    profit = sum(i["qty"] * (i["price"] - i["cost"]) for i in st.session_state["cart"])
    for i in st.session_state["cart"]:
        st.write(f"- {i['name']} x {i['qty']} = {i['qty'] * i['price']:.2f} บาท")
    st.info(f"💰 รวม: {total:.2f} บาท | 🟢 กำไร: {profit:.2f} บาท")

    paid = st.number_input("💵 รับเงิน", min_value=0.0, step=1.0, key="paid_input")
    if paid >= total:
        st.success(f"เงินทอน: {paid - total:.2f} บาท")
    else:
        st.warning("❗ รับเงินไม่พอ")

    if st.button("✅ ยืนยันการขาย"):
        for i in st.session_state["cart"]:
            idx = df[df["ชื่อสินค้า"] == i["name"]].index[0] + 2
            sheet.update_cell(idx, 7, int(sheet.cell(idx, 7).value or 0) + i["qty"])
            sheet.update_cell(idx, 5, int(sheet.cell(idx, 5).value or 0) - i["qty"])
            sheet_sales.append_row([
                now_date, i["name"], i["qty"],
                i["qty"] * i["price"],
                i["qty"] * (i["price"] - i["cost"])
            ])
        st.success("✅ บันทึกเรียบร้อย")
        st.session_state["cart"] = []
        st.session_state["paid_input"] = 0.0
        st.session_state["input_name"] = ""
        st.session_state["add_qty"] = 1
        st.experimental_rerun()

# 📦 เติมสินค้า
with st.expander("📦 เติมสินค้า"):
    selected_item = st.selectbox("เลือกสินค้า", product_names, key="restock_item")
    add_amt = st.number_input("จำนวนที่เติม", min_value=1, step=1, key="restock_qty")
    if st.button("📥 ยืนยันเติม"):
        idx = df[df["ชื่อสินค้า"] == selected_item].index[0] + 2
        sheet.update_cell(idx, 6, int(sheet.cell(idx, 6).value or 0) + add_amt)
        sheet.update_cell(idx, 5, int(sheet.cell(idx, 5).value or 0) + add_amt)
        st.success(f"✅ เติม {selected_item} สำเร็จ")

# ✏️ แก้ไขสินค้า
with st.expander("✏️ แก้ไขสินค้า"):
    edit_item = st.selectbox("เลือกรายการ", product_names, key="edit_item")
    idx = df[df["ชื่อสินค้า"] == edit_item].index[0] + 2
    row = df[df["ชื่อสินค้า"] == edit_item].iloc[0]

    price = float(pd.to_numeric(row["ราคาขาย"], errors="coerce") or 0)
    cost = float(pd.to_numeric(row["ต้นทุน"], errors="coerce") or 0)
    stock = int(pd.to_numeric(row["คงเหลือ"], errors="coerce") or 0)

    new_price = st.number_input("ราคาขายใหม่", value=price, key="edit_price")
    new_cost = st.number_input("ต้นทุนใหม่", value=cost, key="edit_cost")
    new_stock = st.number_input("คงเหลือใหม่", value=stock, step=1, key="edit_stock")

    if st.button("💾 บันทึกการแก้ไข"):
        sheet.update_cell(idx, 3, new_price)
        sheet.update_cell(idx, 4, new_cost)
        sheet.update_cell(idx, 5, new_stock)
        st.success("✅ อัปเดตสำเร็จ")
