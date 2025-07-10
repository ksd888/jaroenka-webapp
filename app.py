import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# เชื่อมต่อ Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
client = gspread.authorize(creds)
spreadsheet = client.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
sheet = spreadsheet.worksheet("ตู้เย็น")

# โหลดข้อมูล
data = sheet.get_all_records()
df = pd.DataFrame(data)

st.title("🧊 ร้านเจริญค้า - ระบบขายสินค้า")

# ระบบค้นหา
search_term = st.text_input("🔍 ค้นหาสินค้า", "")
filtered_df = df[df["ชื่อสินค้า"].str.contains(search_term, case=False, na=False)]

# สร้างตะกร้า
if "cart" not in st.session_state:
    st.session_state.cart = {}

# แสดงผลลัพธ์การค้นหา
for index, row in filtered_df.iterrows():
    st.markdown(f"**{row['ชื่อสินค้า']}**")
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("-", key=f"sub_{row['ชื่อสินค้า']}"):
            if row['ชื่อสินค้า'] in st.session_state.cart and st.session_state.cart[row['ชื่อสินค้า']] > 0:
                st.session_state.cart[row['ชื่อสินค้า']] -= 1
    with col2:
        qty = st.session_state.cart.get(row['ชื่อสินค้า'], 0)
        st.markdown(f"จำนวน: **{qty}**")
    with col3:
        if st.button("+", key=f"add_{row['ชื่อสินค้า']}"):
            st.session_state.cart[row['ชื่อสินค้า']] = st.session_state.cart.get(row['ชื่อสินค้า'], 0) + 1

st.markdown("---")
st.subheader("🛒 ตะกร้าสินค้า")

# สรุปยอดในตะกร้า
total_price = 0
total_profit = 0
for product, qty in st.session_state.cart.items():
    item_row = df[df["ชื่อสินค้า"] == product].iloc[0]
    price = item_row["ราคาขาย"]
    cost = item_row["ต้นทุน"]
    profit = (price - cost) * qty
    total = price * qty
    st.write(f"{product} x {qty} = {total:.2f} บาท")
    total_price += total
    total_profit += profit

st.info(f"📦 ยอดรวม: {total_price:.2f} บาท 🟢 กำไร: {total_profit:.2f} บาท")

# รับเงิน
money = st.number_input("💰 รับเงิน", min_value=0.0, format="%.2f")
if money < total_price:
    st.warning("❌ ยอดเงินไม่พอ")
else:
    if st.button("✅ ยืนยันการขาย"):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for product, qty in st.session_state.cart.items():
            sheet.insert_row([now, product, qty], index=2)
        st.success("✅ บันทึกการขายเรียบร้อยแล้ว")
        st.session_state.cart = {}  # รีเซ็ตตะกร้า
        st.experimental_rerun()
