import streamlit as st
import gspread
from google.oauth2 import service_account
from datetime import datetime
import pandas as pd

# ✅ โหลด credentials จาก secrets.toml
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
    st.session_state["cart"] = []
if "add_qty" not in st.session_state:
    st.session_state["add_qty"] = 1
if "add_name" not in st.session_state:
    st.session_state["add_name"] = ""

# ✅ UI ขายสินค้า
st.title("🧊 ระบบขายสินค้า - ร้านเจริญค้า")
st.header("🛒 ขายสินค้า (พิมพ์ชื่อ + กด ➕ เพิ่มทันที)")

product_names = sorted(df["ชื่อสินค้า"].tolist())

# ✅ ช่องค้นหาแบบ autocomplete
user_input = st.text_input("🔍 ค้นหาสินค้า", value=st.session_state["add_name"], key="product_search")
suggestions = [p for p in product_names if user_input.strip().lower() in p.lower()]

if suggestions and user_input.strip():
    st.caption("📌 คลิกเพื่อเลือกสินค้า:")
    for s in suggestions[:5]:
        if st.button(f"➕ {s}"):
            st.session_state["add_name"] = s
            st.experimental_rerun()

selected_qty = st.number_input("จำนวน", min_value=1, step=1, key="add_qty")

if st.button("➕ เพิ่มลงตะกร้า"):
    match = [p for p in product_names if p.lower() == st.session_state["add_name"].strip().lower()]
    if match:
        selected_product = match[0]
        item = df[df["ชื่อสินค้า"] == selected_product].iloc[0]
        try:
            price = float(pd.to_numeric(item["ราคาขาย"], errors='coerce'))
            cost = float(pd.to_numeric(item["ต้นทุน"], errors='coerce'))
        except:
            st.error("⚠️ ราคาหรือต้นทุนไม่ถูกต้อง")
            price, cost = 0, 0
        st.session_state["cart"].append({
            "name": selected_product,
            "qty": selected_qty,
            "price": price,
            "cost": cost
        })
        st.success(f"✅ เพิ่ม {selected_product} x {selected_qty} สำเร็จ")
        st.session_state["add_qty"] = 1
        st.session_state["add_name"] = ""
        st.experimental_rerun()
    else:
        st.warning("❌ ไม่พบสินค้าที่พิมพ์ กรุณาตรวจสอบชื่อ")

# ✅ แสดงตะกร้า
if st.session_state["cart"]:
    st.subheader("🧾 รายการขาย")
    total, profit_total = 0, 0
    for item in st.session_state["cart"]:
        subtotal = item["qty"] * item["price"]
        profit = item["qty"] * (item["price"] - item["cost"])
        total += subtotal
        profit_total += profit
        st.write(f"- {item['name']} x {item['qty']} = {subtotal:.2f} บาท")

    st.info(f"💵 ยอดรวม: {total:.2f} บาท | 🟢 กำไร: {profit_total:.2f} บาท")
    paid = st.number_input("💰 รับเงิน", min_value=0.0, step=1.0, key="paid_input")
    if paid >= total:
        st.success(f"เงินทอน: {paid - total:.2f} บาท")
    else:
        st.warning("ยอดเงินไม่พอ")

    if st.button("✅ ยืนยันการขาย"):
        for item in st.session_state["cart"]:
            idx = df[df["ชื่อสินค้า"] == item["name"]].index[0] + 2
            qty = int(item["qty"])
            price = float(item["price"])
            cost = float(item["cost"])
            subtotal = round(qty * price, 2)
            profit = round(qty * (price - cost), 2)

            sheet.update_cell(idx, 7, int(sheet.cell(idx, 7).value or 0) + qty)
            sheet.update_cell(idx, 5, int(sheet.cell(idx, 5).value or 0) - qty)

            sheet_sales.append_row([
                now_date,
                str(item["name"]),
                int(qty),
                float(subtotal),
                float(profit)
            ])
        st.success("✅ บันทึกยอดขายเรียบร้อยแล้ว")
        st.session_state["cart"] = []
        st.session_state["paid_input"] = 0.0
        st.session_state["add_qty"] = 1
        st.session_state["add_name"] = ""
        st.experimental_rerun()

# ------------------------
# 📦 เติมสินค้า
# ------------------------
with st.expander("📦 เติมสินค้า"):
    selected_item = st.selectbox("เลือกสินค้า", product_names, key="restock_item")
    add_amount = st.number_input("จำนวนที่เติม", min_value=1, step=1, key="restock_qty")
    if st.button("📥 ยืนยันเติมสินค้า"):
        idx = df[df["ชื่อสินค้า"] == selected_item].index[0] + 2
        sheet.update_cell(idx, 6, int(sheet.cell(idx, 6).value or 0) + add_amount)
        sheet.update_cell(idx, 5, int(sheet.cell(idx, 5).value or 0) + add_amount)
        st.success(f"✅ เติม {selected_item} จำนวน {add_amount} สำเร็จแล้ว")

# ------------------------
# ✏️ แก้ไขสินค้า
# ------------------------
with st.expander("✏️ แก้ไขสินค้า"):
    edit_item = st.selectbox("เลือกรายการ", product_names, key="edit_item")
    idx = df[df["ชื่อสินค้า"] == edit_item].index[0] + 2
    default_row = df[df["ชื่อสินค้า"] == edit_item].iloc[0]

    def safe_float(val):
        try:
            return float(pd.to_numeric(val, errors='coerce')) or 0.0
        except:
            return 0.0

    def safe_int(val):
        try:
            return int(pd.to_numeric(val, errors='coerce')) or 0
        except:
            return 0

    price_val = safe_float(default_row["ราคาขาย"])
    cost_val = safe_float(default_row["ต้นทุน"])
    stock_val = safe_int(default_row["คงเหลือ"])

    new_price = st.number_input("ราคาขายใหม่", value=price_val, key="edit_price")
    new_cost = st.number_input("ต้นทุนใหม่", value=cost_val, key="edit_cost")
    new_stock = st.number_input("คงเหลือใหม่", value=stock_val, step=1, key="edit_stock")

    if st.button("💾 บันทึกการแก้ไข"):
        sheet.update_cell(idx, 3, new_price)
        sheet.update_cell(idx, 4, new_cost)
        sheet.update_cell(idx, 5, new_stock)
        st.success(f"✅ อัปเดต {edit_item} เรียบร้อยแล้ว")
