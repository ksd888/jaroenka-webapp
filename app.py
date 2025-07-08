import streamlit as st
import gspread
from google.oauth2 import service_account
from datetime import datetime
import pandas as pd

# ✅ โหลด credentials จาก secrets
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

# ✅ Session สำหรับขาย
if "cart" not in st.session_state:
    st.session_state.cart = []

# ✅ UI
st.title("🧊 ระบบจัดการสินค้าตู้เย็น - ร้านเจริญค้า")

# --------------------
# 🛒 ระบบขายสินค้า
# --------------------
st.header("🛒 ขายสินค้า")
col1, col2 = st.columns([3, 1])
with col1:
    search_product = st.text_input("🔍 ค้นหาสินค้า")
with col2:
    qty_to_add = st.number_input("จำนวน", min_value=1, step=1, value=1)

# ปุ่ม ➕ เพิ่มสินค้า
matched = df[df["ชื่อสินค้า"].str.contains(search_product, case=False, na=False)]
if not matched.empty:
    product = matched.iloc[0]
    if st.button("➕ เพิ่มสินค้า"):
        st.session_state.cart.append({
            "name": product["ชื่อสินค้า"],
            "qty": qty_to_add,
            "price": product["ราคาขาย"],
            "cost": product["ต้นทุน"]
        })
        st.success(f"เพิ่ม {product['ชื่อสินค้า']} x {qty_to_add}")

# แสดงตะกร้า
if st.session_state.cart:
    st.subheader("🧾 รายการขาย")
    total, total_profit = 0, 0
    for item in st.session_state.cart:
        subtotal = item["qty"] * item["price"]
        profit = item["qty"] * (item["price"] - item["cost"])
        total += subtotal
        total_profit += profit
        st.write(f"- {item['name']} x {item['qty']} = {subtotal} บาท")

    st.info(f"💵 ยอดรวม: {total:.2f} บาท | 🟢 กำไร: {total_profit:.2f} บาท")

    paid = st.number_input("💰 รับเงินจากลูกค้า", min_value=0.0, step=1.0)
    if paid >= total:
        st.success(f"เงินทอน: {paid - total:.2f} บาท")
    else:
        st.warning("ยอดเงินยังไม่พอ")

    if st.button("✅ ยืนยันการขาย"):
        for item in st.session_state.cart:
            idx = df[df["ชื่อสินค้า"] == item["name"]].index[0] + 2
            sheet.update_cell(idx, 7, int(sheet.cell(idx, 7).value or 0) + item["qty"])
            sheet.update_cell(idx, 5, int(sheet.cell(idx, 5).value or 0) - item["qty"])
            sheet_sales.append_row([
                now_date,
                str(item["name"]),
                str(item["qty"]),
                str(item["qty"] * item["price"]),
                str(item["qty"] * (item["price"] - item["cost"]))
            ])
        st.success("✅ บันทึกยอดขายเรียบร้อยแล้ว")
        st.session_state.cart = []

# --------------------
# ➕ เติมสินค้า
# --------------------
with st.expander("➕ เติมสินค้า"):
    item_to_add = st.selectbox("เลือกสินค้า", df["ชื่อสินค้า"].tolist(), key="restock_item")
    amount_to_add = st.number_input("จำนวนที่เติม", min_value=1, step=1, key="restock_qty")
    if st.button("📦 ยืนยันการเติม"):
        idx = df[df["ชื่อสินค้า"] == item_to_add].index[0] + 2
        sheet.update_cell(idx, 6, int(sheet.cell(idx, 6).value or 0) + amount_to_add)
        sheet.update_cell(idx, 5, int(sheet.cell(idx, 5).value or 0) + amount_to_add)
        st.success(f"✅ เติม {item_to_add} เรียบร้อยแล้ว")

# --------------------
# ✏️ แก้ไขสินค้า
# --------------------
with st.expander("✏️ แก้ไขสินค้า"):
    edit_item = st.selectbox("เลือกรายการ", df["ชื่อสินค้า"].tolist(), key="edit_item")
    idx = df[df["ชื่อสินค้า"] == edit_item].index[0] + 2
    new_price = st.number_input("ราคาขายใหม่", value=float(df.loc[idx - 2, "ราคาขาย"]))
    new_cost = st.number_input("ต้นทุนใหม่", value=float(df.loc[idx - 2, "ต้นทุน"]))
    new_stock = st.number_input("คงเหลือใหม่", value=int(df.loc[idx - 2, "คงเหลือ"]), step=1)
    if st.button("💾 บันทึกการแก้ไข"):
        sheet.update_cell(idx, 3, new_price)
        sheet.update_cell(idx, 4, new_cost)
        sheet.update_cell(idx, 5, new_stock)
        st.success(f"✅ อัปเดตรายการ {edit_item} เรียบร้อย")
