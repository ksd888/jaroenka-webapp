import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd

# โหลด credentials จาก secrets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope)
client = gspread.authorize(creds)

# เปิดชีท
spreadsheet = client.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
sheet = spreadsheet.worksheet("ตู้เย็น")
sheet_meta = spreadsheet.worksheet("Meta")
sheet_sales = spreadsheet.worksheet("ยอดขาย")

# รีเซ็ตรายวัน
now_date = datetime.now().strftime("%Y-%m-%d")
last_date = sheet_meta.acell("B1").value
if last_date != now_date:
    sheet.batch_update([{
        'range': 'F2:G1000',
        'values': [[0, 0]] * 999
    }])
    sheet_meta.update("B1", [[now_date]])

# โหลดข้อมูล
data = sheet.get_all_records()
df = pd.DataFrame(data)

# สร้าง session state สำหรับรายการขาย
if "cart" not in st.session_state:
    st.session_state.cart = []

# UI
st.title("🧊 ระบบขายสินค้า - ร้านเจริญค้า")

# --- เพิ่มสินค้า ---
st.header("🛒 ค้นหาและเพิ่มสินค้า")
search_term = st.text_input("🔍 พิมพ์ชื่อสินค้า")
filtered = df[df["ชื่อสินค้า"].str.contains(search_term, case=False, na=False)] if search_term else df.iloc[0:0]

if not filtered.empty:
    product = filtered.iloc[0]
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write(f"**{product['ชื่อสินค้า']}** (ขาย {product['ราคาขาย']} บาท)")
    with col2:
        qty = st.number_input("จำนวน", min_value=1, step=1, key="qty_input")

    if st.button("➕ เพิ่มลงรายการขาย"):
        st.session_state.cart.append({
            "name": product["ชื่อสินค้า"],
            "qty": qty,
            "price": product["ราคาขาย"],
            "cost": product["ต้นทุน"]
        })
        st.success(f"เพิ่ม {product['ชื่อสินค้า']} x {qty} สำเร็จ")

# --- แสดงตะกร้าสินค้า ---
if st.session_state.cart:
    st.subheader("🧾 รายการที่จะขาย")
    total = 0
    total_profit = 0
    for item in st.session_state.cart:
        subtotal = item["qty"] * item["price"]
        profit = item["qty"] * (item["price"] - item["cost"])
        total += subtotal
        total_profit += profit
        st.write(f"- {item['name']} x {item['qty']} = {subtotal} บาท")

    st.info(f"💵 ยอดรวม: {total} บาท / 🟢 กำไร: {total_profit} บาท")
    paid = st.number_input("💰 รับเงิน", min_value=0, step=1, key="paid_input")
    if paid >= total:
        st.success(f"เงินทอน: {paid - total} บาท")
    else:
        st.warning("💡 เงินไม่พอชำระ")

    if st.button("✅ ยืนยันการขาย"):
        for item in st.session_state.cart:
            idx = df[df["ชื่อสินค้า"] == item["name"]].index[0] + 2
            old_out = sheet.cell(idx, 7).value or "0"
            old_left = sheet.cell(idx, 5).value or "0"
            sheet.update_cell(idx, 7, int(old_out) + item["qty"])
            sheet.update_cell(idx, 5, int(old_left) - item["qty"])
            sheet_sales.append_row([
                now_date, item["name"], item["qty"],
                item["qty"] * item["price"],
                item["qty"] * (item["price"] - item["cost"])
            ])
        st.success("✅ บันทึกยอดขายเรียบร้อยแล้ว")

        # 🔄 ล้างตะกร้าหลังบันทึก
        st.session_state.cart.clear()
        st.session_state.qty_input = 1
        st.session_state.paid_input = 0
