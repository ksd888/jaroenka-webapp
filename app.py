import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ตั้งค่าขอบเขตสิทธิ์
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# โหลดข้อมูลจาก secrets หรือไฟล์ service_account.json
creds = Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"], scopes=SCOPES
)
gc = gspread.authorize(creds)

# เปิด Google Sheet
spreadsheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
sheet = spreadsheet.worksheet("ตู้เย็น")

# โหลดข้อมูล Google Sheet
data = sheet.get_all_records()
df = pd.DataFrame(data)

st.title("🧊 ร้านเจริญค้า - ระบบขายสินค้า")

# ฟังก์ชันค้นหาปลอดภัย
def safe_key(key):
    return key.replace(" ", "_").replace(".", "_")

# ค้นหาสินค้า
search_term = st.text_input("🔍 ค้นหาสินค้า", key="search")
filtered_df = df[df["ชื่อสินค้า"].str.contains(search_term, case=False, na=False)] if search_term else df

# สร้างตะกร้าสินค้าใน session state
if "cart" not in st.session_state:
    st.session_state.cart = {}

# แสดงสินค้าให้เลือก
selected_products = st.multiselect("🛒 เลือกสินค้าจากชื่อ", filtered_df["ชื่อสินค้า"].tolist())

# เพิ่มสินค้าเข้าตะกร้า
for p in selected_products:
    row = df[df["ชื่อสินค้า"] == p].iloc[0]
    col1, col2, col3 = st.columns([3,1,1])
    with col1:
        st.markdown(f"**{row['ชื่อสินค้า']}**")
    with col2:
        if st.button("-", key=f"sub_{safe_key(p)}"):
            st.session_state.cart[p] = max(0, st.session_state.cart.get(p, 1) - 1)
    with col3:
        if st.button("+", key=f"add_{safe_key(p)}"):
            st.session_state.cart[p] = st.session_state.cart.get(p, 0) + 1

    if p in st.session_state.cart:
        st.markdown(f"จำนวนที่เลือก: {st.session_state.cart[p]}")

    st.divider()

if st.button("➕ เพิ่มลงตะกร้า"):
    st.success("✅ เพิ่มสินค้าลงตะกร้าแล้ว")

# แสดงรายการขาย
if st.session_state.cart:
    st.markdown("📋 **รายการขาย**")
    total = 0
    profit = 0
    for name, qty in st.session_state.cart.items():
        row = df[df["ชื่อสินค้า"] == name].iloc[0]
        price = row["ราคาขาย"]
        cost = row["ต้นทุน"]
        st.write(f"{name} x {qty} = {qty * price:.2f} บาท")
        total += qty * price
        profit += qty * (price - cost)
    st.info(f"💰 ยอดรวม: {total:.2f} บาท   🟢 กำไร: {profit:.2f} บาท")

    cash = st.number_input("💰 เงินรับ", min_value=0.0, format="%.2f")
    if cash < total:
        st.warning("❌ ยอดเงินไม่พอ")
    else:
        change = cash - total
        st.success(f"✅ เงินทอน: {change:.2f} บาท")

    if st.button("✅ ยืนยันการขาย"):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for name, qty in st.session_state.cart.items():
            row = df[df["ชื่อสินค้า"] == name].iloc[0]
            price = row["ราคาขาย"]
            cost = row["ต้นทุน"]
            sheet_to_write = spreadsheet.worksheet("ยอดขาย")
            sheet_to_write.append_row([now, name, qty, price, cost, price - cost, qty * (price - cost)])
        st.success("📝 บันทึกยอดขายแล้ว")
        st.session_state.cart = {}
        st.experimental_rerun()
