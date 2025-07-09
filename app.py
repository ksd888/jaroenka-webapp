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

# ✅ เปิดชีท
spreadsheet = client.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
sheet = spreadsheet.worksheet("ตู้เย็น")
sheet_meta = spreadsheet.worksheet("Meta")
sheet_sales = spreadsheet.worksheet("ยอดขาย")

# ✅ รีเซ็ตยอดเข้าออกเมื่อวันใหม่
now_date = datetime.now().strftime("%Y-%m-%d")
last_date = sheet_meta.acell("B1").value
if last_date != now_date:
    sheet.batch_update([{
        'range': 'F2:G1000',
        'values': [[0, 0]] * 999
    }])
    sheet_meta.update("B1", [[now_date]])

# ✅ โหลดข้อมูลสินค้า
data = sheet.get_all_records()
df = pd.DataFrame(data)
product_names = sorted(df["ชื่อสินค้า"].dropna().tolist())

# ✅ กำหนด session_state
st.session_state.setdefault("cart", [])
st.session_state.setdefault("paid_input", 0.0)

# ✅ UI หลัก
st.title("🧊 ระบบขายสินค้า - ร้านเจริญค้า")
st.header("🛒 เลือกสินค้าหลายรายการ")

selected_items = st.multiselect("🔍 เลือกสินค้า", product_names)
quantities = {}

for name in selected_items:
    qty = st.number_input(f"จำนวน - {name}", min_value=1, step=1, key=f"qty_{name}")
    quantities[name] = qty

if st.button("➕ เพิ่มลงตะกร้า"):
    for name in selected_items:
        item = df[df["ชื่อสินค้า"] == name].iloc[0]
        try:
            price = float(pd.to_numeric(item["ราคาขาย"], errors='coerce'))
            cost = float(pd.to_numeric(item["ต้นทุน"], errors='coerce'))
            qty = quantities[name]
            st.session_state["cart"].append({
                "name": name,
                "qty": qty,
                "price": price,
                "cost": cost
            })
        except:
            st.warning(f"⚠️ {name} ไม่สามารถเพิ่มได้ (ราคาหรือต้นทุนไม่ถูกต้อง)")
    st.success("✅ เพิ่มลงตะกร้าแล้ว")
    st.stop()

# ✅ ตะกร้าสินค้า
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
            qty = item["qty"]
            price = item["price"]
            cost = item["cost"]
            subtotal = round(qty * price, 2)
            profit = round(qty * (price - cost), 2)

            sheet.update_cell(idx, 7, int(sheet.cell(idx, 7).value or 0) + qty)
            sheet.update_cell(idx, 5, int(sheet.cell(idx, 5).value or 0) - qty)

            sheet_sales.append_row([
                now_date, item["name"], qty, subtotal, profit
            ])

        st.success("✅ บันทึกยอดขายเรียบร้อยแล้ว")
        st.session_state["cart"].clear()
        st.session_state["paid_input"] = 0.0
        st.stop()

# ✅ เติมสินค้า
with st.expander("📦 เติมสินค้า"):
    item = st.selectbox("เลือกสินค้า", product_names, key="restock_item")
    amount = st.number_input("จำนวน", min_value=1, step=1, key="restock_qty")
    if st.button("📥 เติมสินค้า"):
        idx = df[df["ชื่อสินค้า"] == item].index[0] + 2
        sheet.update_cell(idx, 6, int(sheet.cell(idx, 6).value or 0) + amount)
        sheet.update_cell(idx, 5, int(sheet.cell(idx, 5).value or 0) + amount)
        st.success(f"✅ เติม {item} แล้ว")

# ✅ แก้ไขสินค้า
with st.expander("✏️ แก้ไขสินค้า"):
    item = st.selectbox("เลือกรายการ", product_names, key="edit_item")
    idx = df[df["ชื่อสินค้า"] == item].index[0] + 2
    row = df[df["ชื่อสินค้า"] == item].iloc[0]

    def safe_float(v): 
        try: return float(pd.to_numeric(v, errors='coerce') or 0.0)
        except: return 0.0

    def safe_int(v): 
        try: return int(pd.to_numeric(v, errors='coerce') or 0)
        except: return 0

    price_val = safe_float(row["ราคาขาย"])
    cost_val = safe_float(row["ต้นทุน"])
    stock_val = safe_int(row["คงเหลือ"])

    new_price = st.number_input("ราคาขายใหม่", value=price_val)
    new_cost = st.number_input("ต้นทุนใหม่", value=cost_val)
    new_stock = st.number_input("คงเหลือใหม่", value=stock_val, step=1)

    if st.button("💾 บันทึกการแก้ไข"):
        sheet.update_cell(idx, 3, new_price)
        sheet.update_cell(idx, 4, new_cost)
        sheet.update_cell(idx, 5, new_stock)
        st.success(f"✅ อัปเดต {item} แล้ว")
