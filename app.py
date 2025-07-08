import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd

# --- โหลด credentials จาก Streamlit secrets ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope)
client = gspread.authorize(creds)

# --- เปิด Google Sheet ---
spreadsheet = client.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
sheet = spreadsheet.worksheet("ตู้เย็น")
sheet_meta = spreadsheet.worksheet("Meta")
sheet_sales = spreadsheet.worksheet("ยอดขาย")

# --- รีเซ็ตยอดเข้าออกเมื่อวันใหม่ ---
now_date = datetime.now().strftime("%Y-%m-%d")
last_date = sheet_meta.acell("B1").value
if last_date != now_date:
    sheet.batch_update([{
        'range': 'F2:G1000',
        'values': [[0, 0]] * 999
    }])
    sheet_meta.update("B1", [[now_date]])

# --- โหลดข้อมูลจากชีท ---
data = sheet.get_all_records()
df = pd.DataFrame(data)

# --- Session state สำหรับตะกร้าและเติมสินค้า ---
if "cart" not in st.session_state:
    st.session_state.cart = []
if "restock" not in st.session_state:
    st.session_state.restock = {}

# --- UI: ขายสินค้า ---
st.title("🧊 ระบบขายสินค้า - ร้านเจริญค้า")
st.subheader("🔎 เพิ่มสินค้าลงตะกร้า")

product_names = df["ชื่อสินค้า"].tolist()
product_name = st.selectbox("เลือกสินค้า", product_names)
qty = st.number_input("จำนวน", min_value=1, step=1, key="sell_qty")

if st.button("➕ เพิ่มลงตะกร้า"):
    row = df[df["ชื่อสินค้า"] == product_name].iloc[0]
    st.session_state.cart.append({
        "name": product_name,
        "qty": qty,
        "price": row["ราคาขาย"],
        "cost": row["ต้นทุน"]
    })
    st.success(f"เพิ่ม {product_name} x {qty} แล้ว")

# --- แสดงตะกร้า ---
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
        st.success("✅ บันทึกยอดขายเรียบร้อยแล้ว")
        st.session_state.cart = []
        st.session_state.paid_amount = 0
        st.session_state.sell_qty = 1

# --- UI: เติมสินค้า ---
st.header("➕ เติมสินค้า")
item_restock = st.selectbox("เลือกสินค้าที่ต้องการเติม", product_names, key="restock_select")
amount_restock = st.number_input("จำนวนที่เติม", min_value=1, step=1, key="restock_amount")

if st.button("📦 เติมสินค้า"):
    idx = df[df["ชื่อสินค้า"] == item_restock].index[0] + 2
    sheet.update_cell(idx, 6, int(sheet.cell(idx, 6).value or 0) + amount_restock)
    sheet.update_cell(idx, 5, int(sheet.cell(idx, 5).value or 0) + amount_restock)
    st.success(f"เติมสินค้า {item_restock} จำนวน {amount_restock} สำเร็จ")
    st.session_state.restock["restock_select"] = product_names[0]
    st.session_state.restock["restock_amount"] = 1
