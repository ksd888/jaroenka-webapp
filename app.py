import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import json

st.set_page_config(page_title="ร้านเจริญค้า", layout="wide")

# เชื่อมต่อ Google Sheets
scope = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_info(st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scope)
gc = gspread.authorize(credentials)
spreadsheet = gc.open_by_key("1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE")

sheet = spreadsheet.worksheet("ตู้เย็น")
data = sheet.get_all_records()
df = pd.DataFrame(data)

# ✅ แก้ไขตรงนี้: แปลงราคาขายและต้นทุนเป็นตัวเลข
df["ราคาขาย"] = pd.to_numeric(df["ราคาขาย"], errors="coerce")
df["ต้นทุน"] = pd.to_numeric(df["ต้นทุน"], errors="coerce")
df["กำไรต่อหน่วย"] = df["ราคาขาย"] - df["ต้นทุน"]

# สร้าง cart และตัวแปรสถานะ
if "cart" not in st.session_state:
    st.session_state.cart = {}

if "selected_products" not in st.session_state:
    st.session_state.selected_products = []

st.title("🛒 เลือกสินค้าจากชื่อ")

product_names = df["ชื่อสินค้า"].dropna().tolist()

st.session_state.selected_products = st.multiselect(
    "🛒 เลือกสินค้าจากชื่อ", product_names, default=st.session_state.selected_products
)

# แสดงช่องใส่จำนวน
for product in st.session_state.selected_products:
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("➖", key=f"decrease_{product}"):
            st.session_state.cart[product] = max(0, st.session_state.cart.get(product, 0) - 1)
    with col2:
        if st.button("➕", key=f"increase_{product}"):
            st.session_state.cart[product] = st.session_state.cart.get(product, 0) + 1
    with col3:
        st.write(f"{product}")
        st.write(f"จำนวน: {st.session_state.cart.get(product, 0)}")

# เพิ่มสินค้าลงตะกร้า
if st.button("➕ เพิ่มลงตะกร้า"):
    st.success("✅ เพิ่มสินค้าลงตะกร้าแล้ว")

# แสดงตะกร้า
if st.session_state.cart:
    st.subheader("🧺 ตะกร้าสินค้า")
    total = 0
    profit = 0
    for product, qty in st.session_state.cart.items():
        row = df[df["ชื่อสินค้า"] == product]
        if not row.empty:
            price = float(row["ราคาขาย"].values[0])
            unit_profit = float(row["กำไรต่อหน่วย"].values[0])
            st.write(f"- {product} x {qty} = {price * qty:.2f} บาท")
            total += price * qty
            profit += unit_profit * qty
    st.write(f"💰 **ยอดรวม:** {total:.2f} บาท")
    st.write(f"📈 **กำไร:** {profit:.2f} บาท")

    if st.button("✅ ยืนยันการขาย"):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet2 = spreadsheet.worksheet("ยอดขาย")
        for product, qty in st.session_state.cart.items():
            row = df[df["ชื่อสินค้า"] == product]
            if not row.empty:
                price = float(row["ราคาขาย"].values[0])
                unit_profit = float(row["กำไรต่อหน่วย"].values[0])
                sheet2.append_row([now, product, qty, price * qty, unit_profit * qty, "drink"])
        st.success("✅ ขายสินค้าเรียบร้อยแล้ว!")

        # ✅ รีเซ็ตตะกร้าและรายการที่ค้นหา
        st.session_state.cart = {}
        st.session_state.selected_products = []

st.markdown("---")
st.caption("สร้างโดย ❤️ ร้านเจริญค้า")
