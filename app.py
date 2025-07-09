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
product_names = sorted(df["ชื่อสินค้า"].tolist())

# ✅ Session state
st.session_state.setdefault("cart", [])
st.session_state.setdefault("paid_input", 0.0)

# ✅ UI ขายสินค้า
st.title("🧊 ระบบขายสินค้า - ร้านเจริญค้า")
st.header("🛒 ขายสินค้าหลายรายการ (พิมพ์แล้วเลือกได้ทันที)")

# ✅ ช่องค้นหาแบบ Multiselect
selected_items = st.multiselect("🔍 เลือกสินค้า", product_names)

# ✅ กรอกจำนวนสำหรับแต่ละสินค้า
item_qty = {}
for item in selected_items:
    item_qty[item] = st.number_input(f"จำนวน {item}", min_value=1, step=1, key=f"qty_{item}")

# ✅ เพิ่มลงตะกร้า
if st.button("➕ เพิ่มทั้งหมดลงตะกร้า"):
    for item in selected_items:
        row = df[df["ชื่อสินค้า"] == item].iloc[0]
        try:
            price = float(pd.to_numeric(row["ราคาขาย"], errors="coerce"))
            cost = float(pd.to_numeric(row["ต้นทุน"], errors="coerce"))
        except:
            st.error(f"⚠️ ราคาหรือต้นทุนของ {item} ไม่ถูกต้อง")
            continue
        st.session_state["cart"].append({
            "name": item,
            "qty": item_qty[item],
            "price": price,
            "cost": cost
        })
    st.success("✅ เพิ่มสินค้าทั้งหมดสำเร็จ")

# ✅ แสดงตะกร้า
if st.session_state["cart"]:
    st.subheader("🧾 รายการขาย")
    total = 0
    profit_total = 0
    for item in st.session_state["cart"]:
        subtotal = item["qty"] * item["price"]
        profit = item["qty"] * (item["price"] - item["cost"])
        total += subtotal
        profit_total += profit
        st.write(f"- {item['name']} x {item['qty']} = {subtotal:.2f} บาท")

    st.info(f"💵 ยอดรวม: {total:.2f} บาท | 🟢 กำไร: {profit_total:.2f} บาท")

    paid = st.number_input("💰 รับเงิน", min_value=0.0, step=1.0)
    if paid >= total:
        st.success(f"เงินทอน: {paid - total:.2f} บาท")
    else:
        st.warning("ยอดเงินไม่พอ")

    if st.button("✅ ยืนยันการขาย"):
        for item in st.session_state["cart"]:
            idx = df[df["ชื่อสินค้า"] == item["name"]].index[0] + 2
            qty = item["qty"]
            price = item["price"]
            cost = item["cost"]
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

# ✅ เติมสินค้า
with st.expander("📦 เติมสินค้า"):
    item = st.selectbox("เลือกสินค้า", product_names, key="restock_item")
    amount = st.number_input("จำนวนที่เติม", min_value=1, step=1, key="restock_qty")
    if st.button("📥 ยืนยันเติมสินค้า"):
        idx = df[df["ชื่อสินค้า"] == item].index[0] + 2
        sheet.update_cell(idx, 6, int(sheet.cell(idx, 6).value or 0) + amount)
        sheet.update_cell(idx, 5, int(sheet.cell(idx, 5).value or 0) + amount)
        st.success(f"✅ เติม {item} แล้ว")

# ✅ แก้ไขสินค้า
with st.expander("✏️ แก้ไขสินค้า"):
    item = st.selectbox("เลือกรายการ", product_names, key="edit_item")
    idx = df[df["ชื่อสินค้า"] == item].index[0] + 2
    row = df[df["ชื่อสินค้า"] == item].iloc[0]

    def safe_float(val): return float(pd.to_numeric(val, errors="coerce")) if pd.notna(val) else 0.0
    def safe_int(val): return int(pd.to_numeric(val, errors="coerce")) if pd.notna(val) else 0

    new_price = st.number_input("ราคาขายใหม่", value=safe_float(row["ราคาขาย"]), key="edit_price")
    new_cost = st.number_input("ต้นทุนใหม่", value=safe_float(row["ต้นทุน"]), key="edit_cost")
    new_stock = st.number_input("คงเหลือใหม่", value=safe_int(row["คงเหลือ"]), step=1, key="edit_stock")

    if st.button("💾 บันทึกการแก้ไข"):
        sheet.update_cell(idx, 3, new_price)
        sheet.update_cell(idx, 4, new_cost)
        sheet.update_cell(idx, 5, new_stock)
        st.success("✅ อัปเดตเรียบร้อยแล้ว")
    
