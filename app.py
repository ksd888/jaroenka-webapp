import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd

# --- โหลด credentials จาก secrets ---
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]
creds = Credentials.from_service_account_info(st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope)
client = gspread.authorize(creds)

# --- เปิด Google Sheets ---
spreadsheet = client.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
sheet = spreadsheet.worksheet("ตู้เย็น")
sheet_meta = spreadsheet.worksheet("Meta")
sheet_sales = spreadsheet.worksheet("ยอดขาย")

# --- รีเซ็ตยอดเข้าออกทุกวันใหม่ ---
now_date = datetime.now().strftime("%Y-%m-%d")
last_date = sheet_meta.acell("B1").value
if last_date != now_date:
    sheet.batch_update([{
        'range': 'F2:G1000',
        'values': [[0, 0]] * 999
    }])
    sheet_meta.update("B1", [[now_date]])

# --- โหลดข้อมูลสินค้า ---
data = sheet.get_all_records()
df = pd.DataFrame(data)

# --- สร้าง session state ---
if "cart" not in st.session_state:
    st.session_state.cart = []

# --- UI ส่วนขายสินค้า ---
st.title("🧊 ระบบขายสินค้า - ร้านเจริญค้า")
st.subheader("🛒 เพิ่มสินค้าเข้าตะกร้า")

product_names = df["ชื่อสินค้า"].tolist()
product_name = st.selectbox("เลือกสินค้า", product_names, key="sell_select")
qty = st.number_input("จำนวน", min_value=1, step=1, key="sell_qty")

if st.button("➕ เพิ่มสินค้า"):
    row = df[df["ชื่อสินค้า"] == product_name].iloc[0]
    st.session_state.cart.append({
        "name": product_name,
        "qty": qty,
        "price": row["ราคาขาย"],
        "cost": row["ต้นทุน"]
    })
    st.success(f"เพิ่ม {product_name} x {qty} สำเร็จแล้ว")

# --- แสดงรายการสินค้าในตะกร้า ---
if st.session_state.cart:
    st.subheader("🧾 รายการขาย")
    total, total_profit = 0, 0
    for item in st.session_state.cart:
        subtotal = item["qty"] * item["price"]
        profit = item["qty"] * (item["price"] - item["cost"])
        total += subtotal
        total_profit += profit
        st.write(f"- {item['name']} x {item['qty']} = {subtotal} บาท")

    st.info(f"💵 ยอดรวม: {total} บาท | 🟢 กำไร: {total_profit} บาท")
    paid = st.number_input("💰 รับเงินจากลูกค้า", min_value=0, step=1, key="paid_amount")

    if paid >= total:
        st.success(f"เงินทอน: {paid - total} บาท")
    else:
        st.warning("⚠️ เงินไม่พอชำระ")

    if st.button("✅ ยืนยันการขาย"):
        for item in st.session_state.cart:
            idx = df[df["ชื่อสินค้า"] == item["name"]].index[0] + 2
            out_qty = int(sheet.cell(idx, 7).value or 0)
            remain = int(sheet.cell(idx, 5).value or 0)
            sheet.update_cell(idx, 7, out_qty + item["qty"])
            sheet.update_cell(idx, 5, remain - item["qty"])
            sheet_sales.append_row([
                now_date,
                item["name"],
                item["qty"],
                float(item["qty"]) * float(item["price"]),
                float(item["qty"]) * (float(item["price"]) - float(item["cost"]))
            ])

        st.success("✅ บันทึกยอดขายเรียบร้อยแล้ว")
        st.session_state.cart.clear()
        st.experimental_rerun()

# --- UI ส่วนเติมสินค้า ---
st.header("📦 เติมสินค้าเข้าสต๊อก")
restock_name = st.selectbox("เลือกสินค้าที่จะเติม", product_names, key="restock_select")
restock_qty = st.number_input("จำนวนที่เติม", min_value=1, step=1, key="restock_qty")

if st.button("➕ เติมสินค้า"):
    idx = df[df["ชื่อสินค้า"] == restock_name].index[0] + 2
    in_qty = int(sheet.cell(idx, 6).value or 0)
    remain = int(sheet.cell(idx, 5).value or 0)
    sheet.update_cell(idx, 6, in_qty + restock_qty)
    sheet.update_cell(idx, 5, remain + restock_qty)
    st.success(f"เติมสินค้า {restock_name} จำนวน {restock_qty} สำเร็จ")
    st.experimental_rerun()
