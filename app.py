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
for key, default in {"cart": [], "add_qty": 1, "add_name": ""}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ✅ UI ขายสินค้า
st.title("🧊 ระบบขายสินค้า - ร้านเจริญค้า")
st.header("🛒 ขายสินค้า (พิมพ์ชื่อ + กด ➕ เพิ่มทันที)")

product_names = sorted(df["ชื่อสินค้า"].tolist())
user_input = st.text_input("🔍 ค้นหาสินค้า (พิมพ์ชื่อ)", st.session_state["add_name"], key="input_name")

# ✅ Suggestion guide
suggestions = [p for p in product_names if user_input.strip().lower() in p.lower()]
if suggestions and user_input.strip():
    st.caption("📌 คลิกเพื่อเลือกชื่อสินค้า:")
    for s in suggestions[:5]:
        if st.button(f"➤ {s}", key=f"suggestion_{s}"):
            st.session_state["input_name"] = s
            st.experimental_rerun()

selected_qty = st.number_input("จำนวน", min_value=1, step=1, key="add_qty")

if st.button("➕ เพิ่มลงตะกร้า"):
    match = [p for p in product_names if p.lower() == st.session_state["input_name"].strip().lower()]
    if match:
        selected_product = match[0]
        item = df[df["ชื่อสินค้า"] == selected_product].iloc[0]
        st.session_state["cart"].append({
            "name": selected_product,
            "qty": selected_qty,
            "price": float(item["ราคาขาย"]),
            "cost": float(item["ต้นทุน"])
        })
        st.success(f"✅ เพิ่ม {selected_product} x {selected_qty} สำเร็จ")
        st.session_state["add_qty"] = 1
        st.session_state["input_name"] = ""
        st.experimental_rerun()
    else:
        st.warning("❌ ไม่พบสินค้าที่พิมพ์ กรุณาตรวจสอบชื่อให้ตรง")

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
                item["name"],
                qty,
                subtotal,
                profit
            ])
        st.success("✅ บันทึกยอดขายเรียบร้อยแล้ว")

        st.session_state["cart"] = []
        st.session_state["paid_input"] = 0.0
        st.session_state["input_name"] = ""
        st.session_state["add_qty"] = 1
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

    try:
        price_val = float(pd.to_numeric(default_row["ราคาขาย"], errors='coerce'))
        if pd.isna(price_val): price_val = 0.0
    except: price_val = 0.0

    try:
        cost_val = float(pd.to_numeric(default_row["ต้นทุน"], errors='coerce'))
        if pd.isna(cost_val): cost_val = 0.0
    except: cost_val = 0.0

    try:
        stock_raw = pd.to_numeric(default_row["คงเหลือ"], errors='coerce')
        stock_val = int(stock_raw) if not pd.isna(stock_raw) else 0
    except: stock_val = 0

    new_price = st.number_input("ราคาขายใหม่", value=price_val, key="edit_price")
    new_cost = st.number_input("ต้นทุนใหม่", value=cost_val, key="edit_cost")
    new_stock = st.number_input("คงเหลือใหม่", value=stock_val, step=1, key="edit_stock")

    if st.button("💾 บันทึกการแก้ไข"):
        sheet.update_cell(idx, 3, new_price)
        sheet.update_cell(idx, 4, new_cost)
        sheet.update_cell(idx, 5, new_stock)
        st.success(f"✅ อัปเดต {edit_item} เรียบร้อยแล้ว")
