import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ตั้งค่าการเชื่อมต่อ Google Sheet
scope = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_info(
    st.secrets["GCP_SERVICE_ACCOUNT"],
    scopes=scope
)
gc = gspread.authorize(credentials)

spreadsheet_id = "1HVA9mDcDmyxfKvxQd4V5ZkWh4niq33PwVGY6gwoKnAE"
sheet = gc.open_by_key(spreadsheet_id)
sheet_data = sheet.worksheet("ตู้เย็น")
sheet_log = sheet.worksheet("ยอดขาย")

# โหลดข้อมูลจากชีท
data = sheet_data.get_all_records()
df = pd.DataFrame(data)

# แปลงชื่อคีย์ให้สอดคล้อง
df.columns = [col.strip() for col in df.columns]
if "ชื่อสินค้า" not in df.columns:
    st.error("❌ ไม่พบคอลัมน์: ชื่อสินค้า")
    st.stop()

# Session state
if "cart" not in st.session_state:
    st.session_state.cart = {}

# Helper
def safe_key(s):
    return s.replace(" ", "_").replace("/", "_")

# UI
st.title("🧊 ร้านเจริญค้า - ระบบขายสินค้า")
st.subheader("🛒 เลือกสินค้าจากชื่อ")

product_names = df["ชื่อสินค้า"].tolist()
selected_products = st.multiselect("🧐 เลือกสินค้าจากชื่อ", product_names, key="selected")

# แสดงรายการสินค้าที่เลือก พร้อมจำนวน
for name in selected_products:
    row = df[df["ชื่อสินค้า"] == name].iloc[0]
    key = safe_key(name)
    if key not in st.session_state.cart:
        st.session_state.cart[key] = {"name": name, "qty": 1}

    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("➖", key=f"sub_{key}"):
            if st.session_state.cart[key]["qty"] > 1:
                st.session_state.cart[key]["qty"] -= 1
    with col2:
        if st.button("➕", key=f"add_{key}"):
            st.session_state.cart[key]["qty"] += 1
    with col3:
        st.markdown(f"**{name}** (จำนวน: {st.session_state.cart[key]['qty']})")

if st.button("➕ เพิ่มลงตะกร้า"):
    st.success("✅ เพิ่มสินค้าลงตะกร้าแล้ว")

# ตะกร้า
st.subheader("🧺 ตะกร้าสินค้า")
if not st.session_state.cart:
    st.info("ยังไม่มีสินค้าในตะกร้า")
else:
    total = 0
    profit = 0
    for item in st.session_state.cart.values():
        row = df[df["ชื่อสินค้า"] == item["name"]].iloc[0]
        qty = item["qty"]
        price = float(row["ราคาขาย"])
        cost = float(row["ต้นทุน"])
        total += price * qty
        profit += (price - cost) * qty
        st.markdown(f"- {item['name']} x {qty} = {price * qty:.2f} บาท")

    st.markdown(f"### 💰 ยอดรวม: {total:.2f} บาท")
    st.markdown(f"### 📈 กำไร: {profit:.2f} บาท")

    if st.button("✅ ยืนยันการขาย"):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for item in st.session_state.cart.values():
            row = df[df["ชื่อสินค้า"] == item["name"]].iloc[0]
            price = float(row["ราคาขาย"])
            cost = float(row["ต้นทุน"])
            profit_per_unit = price - cost
            qty = item["qty"]
            sheet_log.append_row([
                now, item["name"], qty, price, cost, price * qty, profit_per_unit * qty
            ])
            # อัปเดตจำนวนออก + คงเหลือ
            idx = df[df["ชื่อสินค้า"] == item["name"]].index[0]
            col_out = df.columns.get_loc("ออก")
            col_remain = df.columns.get_loc("คงเหลือในตู้")
            sheet_data.update_cell(idx + 2, col_out + 1, int(df.iloc[idx, col_out]) + qty)
            sheet_data.update_cell(idx + 2, col_remain + 1, int(df.iloc[idx, col_remain]) - qty)

        st.session_state.cart = {}  # 🔄 รีเซ็ตตะกร้า
        st.success("✅ ขายสินค้าเรียบร้อยแล้ว!")
