from datetime import datetime

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

st.set_page_config(page_title="ร้านเจริญค้า", layout="centered")

# CSS Apple-style
st.markdown("""
    <style>
    body, .main, .block-container {
        background-color: #ffffff !important;
        color: #000000 !important;
    }
    .stButton>button {
        color: white !important;
        background-color: #007aff !important;
        border: none;
        border-radius: 8px;
        padding: 0.5em 1em;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🧊 ระบบขายสินค้า - ร้านเจริญค้า")
st.subheader("🛒 เลือกสินค้า")

# 🔐 เชื่อม Google Sheet
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")
worksheet = sheet.worksheet("ตู้เย็น")
data = worksheet.get_all_records()
df = pd.DataFrame(data)

# เตรียม session state
if "quantities" not in st.session_state:
    st.session_state.quantities = {}
if "cart" not in st.session_state:
    st.session_state.cart = []

# รายการสินค้า
product_names = df["ชื่อสินค้า"].tolist()
selected_items = st.multiselect("🔍 เลือกสินค้าจากชื่อ", product_names)

# วนแสดงสินค้า
for item in selected_items:
    row = df[df["ชื่อสินค้า"] == item].iloc[0]
    price = float(row["ราคาขาย"])
    stock = int(row["คงเหลือ"])

    if item not in st.session_state.quantities:
        st.session_state.quantities[item] = 1

    st.markdown(f"### {item}")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("➖", key=f"dec_{item}"):
            st.session_state.quantities[item] = max(1, st.session_state.quantities[item] - 1)
    with col2:
        qty = st.session_state.quantities[item]
        st.markdown(
            f"<div style='text-align:center; font-size:20px; font-weight:bold'>{qty}</div>",
            unsafe_allow_html=True
        )
    with col3:
        if st.button("➕", key=f"inc_{item}"):
            st.session_state.quantities[item] += 1

    st.markdown(
        f"<span style='color:black; font-size:18px'>🧊 คงเหลือในตู้: {stock}</span>",
        unsafe_allow_html=True
    )

# เพิ่มลงตะกร้า
if st.button("➕ เพิ่มลงตะกร้า"):
    for item in selected_items:
        qty = st.session_state.quantities[item]
        row = df[df["ชื่อสินค้า"] == item].iloc[0]
        price = float(row["ราคาขาย"])
        st.session_state.cart.append({
            "ชื่อสินค้า": item,
            "จำนวน": qty,
            "ราคาขาย": price,
            "รวม": qty * price
        })

# แสดงตะกร้า
if st.session_state.cart:
    st.subheader("🧾 ตะกร้าสินค้า")
    total = 0
    for c in st.session_state.cart:
        st.write(f"• {c['ชื่อสินค้า']} x {c['จำนวน']} = {c['รวม']} บาท")
        total += c["รวม"]
    st.markdown(f"### 💰 ยอดรวม: {total} บาท")

    # ปุ่มบันทึกยอดขาย
    if st.button("✅ บันทึกยอดขาย"):
        ws = sheet.worksheet("ยอดขาย")
        for item in st.session_state.cart:
            ws.append_row([
                item["ชื่อสินค้า"], item["จำนวน"], item["ราคาขาย"], item["รวม"]
            ])
        st.success("บันทึกยอดขายเรียบร้อยแล้ว ✅")
        st.session_state.cart = []


# 🔄 ล้างตะกร้าเมื่อวันเปลี่ยน
today = datetime.now().strftime("%Y-%m-%d")
if "last_sale_date" not in st.session_state:
    st.session_state.last_sale_date = today

if st.session_state.last_sale_date != today:
    st.session_state.cart = []
    st.session_state.quantities = {}
    st.session_state.last_sale_date = today
    st.success("เริ่มต้นวันใหม่ ตะกร้าและจำนวนถูกรีเซ็ตแล้ว ✅")
