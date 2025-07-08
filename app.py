import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd

# --- โหลด credentials จาก secrets ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope)
client = gspread.authorize(creds)

# --- เปิดชีทหลัก ---
spreadsheet = client.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
sheet = spreadsheet.worksheet("ตู้เย็น")
sheet_meta = spreadsheet.worksheet("Meta")
sheet_sales = spreadsheet.worksheet("ยอดขาย")

# --- รีเซ็ตยอดเข้า/ออก ทุกวันใหม่ ---
now_date = datetime.now().strftime("%Y-%m-%d")
last_date = sheet_meta.acell("B1").value
if last_date != now_date:
    sheet.batch_update([{
        'range': 'F2:G1000',
        'values': [[0, 0]] * 999
    }])
    sheet_meta.update("B1", [[now_date]])

# --- โหลดข้อมูล Google Sheet ---
data = sheet.get_all_records()
df = pd.DataFrame(data)

# --- Session state สำหรับตะกร้า/เติมสินค้า ---
if "cart" not in st.session_state:
    st.session_state.cart = []
if "restock" not in st.session_state:
    st.session_state.restock = {}

# --- UI: ขายสินค้า ---
st.title("🧊 ระบบขายสินค้า - ร้านเจริญค้า")
st.subheader("🛒 เพิ่มสินค้าทีละรายการ")

product_names = df["ชื่อสินค้า"].tolist()
selected_name = st.selectbox("🔍 ค้นหาสินค้า", product_names)
sell_qty = st.number_input("จำนวน", min_value=1, step=1, key="sell_qty")

if st.button("➕ เพิ่มลงตะกร้า"):
    row = df[df["ชื่อสินค้า"] == selected_name].iloc[0]
    st.session_state.cart.append({
        "name": selected_name,
        "qty": int(sell_qty),
        "price": float(row["ราคาขาย"]),
        "cost": float(row["ต้นทุน"])
    })
    st.success(f"เพิ่ม {selected_name} x {sell_qty} แล้ว")

# --- แสดงรายการในตะกร้า ---
if st.session_state.cart:
    st.subheader("📦 รายการขาย")
    total, total_profit = 0, 0
    for item in st.session_state.cart:
        subtotal = item["qty"] * item["price"]
        profit = item["qty"] * (item["price"] - item["cost"])
        total += subtotal
        total_profit += profit
        st.write(f"- {item['name']} x {item['qty']} = {subtotal:.2f} บาท")

    st.info(f"💵 ยอดรวม: {total:.2f} บาท | 🟢 กำไร: {total_profit:.2f} บาท")
    paid = st.number_input("💰 รับเงิน", min_value=0.0, step=1.0, key="paid_amount")
    if paid >= total:
        st.success(f"เงินทอน: {paid - total:.2f} บาท")
    else:
        st.warning("⚠️ เงินไม่พอชำระ")

    if st.button("✅ ยืนยันการขาย"):
        for item in st.session_state.cart:
            idx = df[df["ชื่อสินค้า"] == item["name"]].index[0] + 2
            old_out = int(sheet.cell(idx, 7).value or 0)
            old_stock = int(sheet.cell(idx, 5).value or 0)
            sheet.update_cell(idx, 7, old_out + item["qty"])
            sheet.update_cell(idx, 5, old_stock - item["qty"])

            sheet_sales.append_row([
                str(now_date),
                str(item["name"]),
                int(item["qty"]),
                float(item["qty"] * item["price"]),
                float(item["qty"] * (item["price"] - item["cost"]))
            ])
        st.success("✅ บันทึกยอดขายเรียบร้อยแล้ว")

        # 🔄 รีเซ็ตค่าหลังขายเสร็จ
        st.session_state.cart = []
        st.session_state.paid_amount = 0
        st.session_state.sell_qty = 1

# --- UI: เติมสินค้า ---
st.header("🔄 เติมสินค้าเข้าสต๊อก")
restock_name = st.selectbox("เลือกสินค้าเติม", product_names, key="restock_select")
restock_qty = st.number_input("จำนวนที่เติม", min_value=1, step=1, key="restock_amount")

if st.button("📥 ยืนยันการเติม"):
    idx = df[df["ชื่อสินค้า"] == restock_name].index[0] + 2
    old_in = int(sheet.cell(idx, 6).value or 0)
    old_stock = int(sheet.cell(idx, 5).value or 0)
    sheet.update_cell(idx, 6, old_in + restock_qty)
    sheet.update_cell(idx, 5, old_stock + restock_qty)
    st.success(f"เติม {restock_name} จำนวน {restock_qty} สำเร็จ")

    # 🔄 รีเซ็ตค่าหลังเติมเสร็จ
    st.session_state.restock["restock_select"] = product_names[0]
    st.session_state.restock["restock_amount"] = 1
