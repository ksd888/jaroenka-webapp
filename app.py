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
product_names = df["ชื่อสินค้า"].tolist()

# --- Session state ---
if "cart" not in st.session_state:
    st.session_state.cart = []

# --- UI ---
st.title("🧊 ระบบขายสินค้า - ร้านเจริญค้า")
st.subheader("🛒 เพิ่มสินค้าลงรายการขาย")

# --- ระบบ autocomplete + ปุ่มเพิ่มทีละตัว ---
col1, col2 = st.columns([3, 1])
with col1:
    new_product = st.text_input("🔍 ค้นหาสินค้า", placeholder="เช่น โค้ก, คาราบาว...")
with col2:
    qty = st.number_input("จำนวน", min_value=1, step=1, key="qty_input")

# เพิ่มสินค้าเมื่อกด +
if st.button("➕ เพิ่ม"):
    match = df[df["ชื่อสินค้า"].str.contains(new_product, case=False, na=False)]
    if not match.empty:
        item = match.iloc[0]
        st.session_state.cart.append({
            "name": item["ชื่อสินค้า"],
            "qty": qty,
            "price": item["ราคาขาย"],
            "cost": item["ต้นทุน"]
        })
        st.success(f"✅ เพิ่ม {item['ชื่อสินค้า']} x {qty} แล้ว")
    else:
        st.error("❌ ไม่พบสินค้านี้ในระบบ")

# --- แสดงตะกร้า ---
if st.session_state.cart:
    st.subheader("📦 รายการขาย")
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
        st.warning("💡 รับเงินยังไม่พอ")

    if st.button("✅ ยืนยันการขาย"):
        for item in st.session_state.cart:
            idx = df[df["ชื่อสินค้า"] == item["name"]].index[0] + 2
            old_out = int(sheet.cell(idx, 7).value or 0)
            old_left = int(sheet.cell(idx, 5).value or 0)
            sheet.update_cell(idx, 7, old_out + item["qty"])
            sheet.update_cell(idx, 5, old_left - item["qty"])
            sheet_sales.append_row([
                str(now_date),
                str(item["name"]),
                int(item["qty"]),
                float(item["qty"] * item["price"]),
                float(item["qty"] * (item["price"] - item["cost"]))
            ])
        st.success("✅ บันทึกยอดขายแล้ว")
        st.session_state.cart.clear()

# --- เติมสินค้า ---
st.header("📦 เติมสินค้า")
colx1, colx2 = st.columns([3, 1])
with colx1:
    restock_product = st.text_input("🔍 ค้นหาสำหรับเติม", key="restock_input", placeholder="เช่น ลิโพ, น้ำถัง")
with colx2:
    restock_qty = st.number_input("จำนวน", min_value=1, step=1, key="restock_qty")

if st.button("📥 ยืนยันเติม"):
    match = df[df["ชื่อสินค้า"].str.contains(restock_product, case=False, na=False)]
    if not match.empty:
        idx = match.index[0] + 2
        old_in = int(sheet.cell(idx, 6).value or 0)
        old_left = int(sheet.cell(idx, 5).value or 0)
        sheet.update_cell(idx, 6, old_in + restock_qty)
        sheet.update_cell(idx, 5, old_left + restock_qty)
        st.success(f"✅ เติม {match.iloc[0]['ชื่อสินค้า']} แล้ว")
    else:
        st.error("❌ ไม่พบสินค้านี้สำหรับเติม")
