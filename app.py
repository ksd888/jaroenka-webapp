import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime

# 📌 ฟังก์ชันความปลอดภัย
def safe_int(val):
    try:
        return int(float(val))
    except:
        return 0

def safe_float(val):
    try:
        return float(val)
    except:
        return 0.0

# 🔐 Auth
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope)
gc = gspread.authorize(credentials)

# 📗 เปิดชีท
sheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
ws = sheet.worksheet("ตู้เย็น")
summary_ws = sheet.worksheet("ยอดขาย")

# 📊 โหลดข้อมูล
df = pd.DataFrame(ws.get_all_records())

# 🧠 ตั้งค่าเริ่มต้น
if "cart" not in st.session_state: st.session_state.cart = []
if "quantities" not in st.session_state: st.session_state.quantities = {}
if "paid" not in st.session_state: st.session_state.paid = 0.0

# 🛒 หน้าขาย
st.title("ขายสินค้า - ร้านเจริญค้า")
product_names = df["ชื่อสินค้า"].tolist()
selected = st.multiselect("เลือกสินค้า", product_names)

for p in selected:
    if p not in st.session_state.quantities:
        st.session_state.quantities[p] = 1
    col1, col2, col3 = st.columns([3,1,1])
    with col1: st.write(p)
    with col2:
        if st.button("➖", key=f"dec_{p}"):
            st.session_state.quantities[p] = max(1, st.session_state.quantities[p] - 1)
    with col3:
        if st.button("➕", key=f"inc_{p}"):
            st.session_state.quantities[p] += 1

if st.button("เพิ่มลงตะกร้า"):
    for p in selected:
        qty = safe_int(st.session_state.quantities[p])
        st.session_state.cart.append((p, qty))
    st.success("เพิ่มสินค้าแล้ว")
    st.session_state.quantities = {}
    st.experimental_rerun()

# 🧾 แสดงตะกร้า
if st.session_state.cart:
    st.subheader("ตะกร้าสินค้า")
    total, profit = 0, 0
    for item, qty in st.session_state.cart:
        row = df[df["ชื่อสินค้า"] == item].iloc[0]
        price = safe_float(row["ราคาขาย"])
        cost = safe_float(row["ต้นทุน"])
        total += qty * price
        profit += qty * (price - cost)
        st.write(f"{item} x {qty} = {qty * price:.2f} บาท")

    st.info(f"รวม: {total:.2f} บาท | กำไร: {profit:.2f} บาท")
    st.session_state.paid = st.number_input("รับเงิน", value=st.session_state.paid, step=1.0)
    if st.session_state.paid >= total:
        st.success(f"เงินทอน: {st.session_state.paid - total:.2f} บาท")
    else:
        st.warning("เงินไม่พอ")

    if st.button("✅ ยืนยันการขาย"):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        summary_ws.append_row([
            now,
            ", ".join([f"{i} x {q}" for i, q in st.session_state.cart]),
            total,
            profit,
            st.session_state.paid,
            st.session_state.paid - total,
            "drink"
        ])
        st.session_state.cart = []
        st.session_state.paid = 0.0
        st.success("✅ ขายเสร็จแล้ว")
        st.experimental_rerun()
